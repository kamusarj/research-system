import json

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.identity import current_actor_id
from app.models import (
    AuditEvent,
    ConceptAlias,
    DocumentGraphWorkspace,
    GraphChangeSet,
    GraphMutation,
    KnowledgeEdge,
    KnowledgeNode,
    NodeEvidence,
    utcnow,
)
from app.schemas.graph_changes import (
    GraphChangeSetRead,
    GraphMutationRead,
    MutationDecisionRequest,
)
from app.services.object_storage import DocumentError
from app.services.ontology import normalize_ontology_key, validate_placement
from app.services.ontology_mapping import ALLOWED_EDGE_TYPES
from app.services.projection_state import mark_canonical_graph_changed

# Chỉ bộ thay đổi ở hai trạng thái này còn được sửa/kiểm tra lại; các trạng thái sau
# (approved, rejected, applied, compensated) chỉ đi tiếp theo thao tác của chủ sở hữu.
EDITABLE_STATUSES = frozenset({"draft", "needs_review"})
TARGET_LIFECYCLE_STATUSES = frozenset({"approved", "archived", "superseded"})


def get_change_set(db: Session, change_set_id: str) -> GraphChangeSet:
    item = db.get(GraphChangeSet, change_set_id)
    if item is None:
        raise DocumentError("CHANGE_SET_NOT_FOUND", "Graph change set not found", 404)
    return item


def _lock_change_set(db: Session, change_set_id: str) -> GraphChangeSet:
    # populate_existing: phiên đã nạp đối tượng này trước đó, nếu không làm mới thì trạng thái
    # đọc được sau khi chờ khóa vẫn là giá trị cũ và hai lượt duyệt/áp dụng song song cùng chạy.
    locked = db.scalar(
        select(GraphChangeSet)
        .where(GraphChangeSet.id == change_set_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if locked is None:
        raise DocumentError("CHANGE_SET_NOT_FOUND", "Graph change set not found", 404)
    return locked


def change_set_mutations(db: Session, change_set_id: str) -> list[GraphMutation]:
    return list(
        db.scalars(
            select(GraphMutation)
            .where(GraphMutation.change_set_id == change_set_id)
            .order_by(GraphMutation.mutation_order)
        )
    )


def serialize_mutation(item: GraphMutation) -> GraphMutationRead:
    return GraphMutationRead(
        id=item.id,
        mutation_order=item.mutation_order,
        operation=item.operation,
        target_kind=item.target_kind,
        target_id=item.target_id,
        before_json=item.before_json or {},
        proposed_json=item.proposed_json or {},
        validation_status=item.validation_status,
        validation_messages=item.validation_messages or [],
        review_decision=item.review_decision,
        reviewed_by=item.reviewed_by,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def serialize_change_set(db: Session, item: GraphChangeSet) -> GraphChangeSetRead:
    return GraphChangeSetRead(
        id=item.id,
        origin_type=item.origin_type,
        origin_id=item.origin_id,
        title=item.title,
        summary=item.summary,
        lifecycle_status=item.lifecycle_status,
        validation_summary=item.validation_summary or {},
        created_by=item.created_by,
        approved_by=item.approved_by,
        applied_at=item.applied_at,
        mutations=[serialize_mutation(mutation) for mutation in change_set_mutations(db, item.id)],
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


VALIDATION_MESSAGES = {
    "EVIDENCE_REQUIRED": "Cần có bằng chứng trước khi áp dụng thay đổi.",
    "INVALID_LABEL": "Nhãn đề xuất chưa hợp lệ.",
    "INVALID_NODE_TYPE": "Loại nút đề xuất chưa hợp lệ.",
    "PARENT_REQUIRED": "Cần chọn nút cha cho đề xuất này.",
    "PARENT_NOT_FOUND": "Không tìm thấy nút cha đã chọn.",
    "ONTOLOGY_PLACEMENT_CONFLICT": "Vị trí đề xuất xung đột với cấu trúc tri thức hiện tại.",
    "DUPLICATE_NODE_CANDIDATE": "Có một nút chuẩn có khả năng bị trùng.",
    "SIMILAR_NODE_CANDIDATE": "Có nút chuẩn tương tự cần được kiểm tra.",
    "TARGET_NOT_FOUND": "Không tìm thấy đối tượng cần thay đổi.",
    "EDGE_TARGET_NOT_FOUND": "Không tìm thấy nút đích của cạnh.",
    "SELF_LOOP": "Một nút không thể tạo quan hệ với chính nó theo cách này.",
    "INVALID_EDGE_TYPE": "Loại cạnh đề xuất chưa hợp lệ.",
    "INVALID_CONFIDENCE": "Độ tin cậy phải nằm trong khoảng hợp lệ.",
    "RELATION_TYPE_REVIEW": "Cần kiểm tra lại loại quan hệ trước khi áp dụng.",
    "INVALID_ALIAS": "Tên thay thế đề xuất chưa hợp lệ.",
    "UNSUPPORTED_MUTATION": "Loại thay đổi này chưa được hỗ trợ.",
    "HIERARCHY_CYCLE": "Thay đổi này sẽ tạo vòng lặp trong cấu trúc phân cấp.",
}


def _message(level: str, code: str, message: str) -> dict[str, str]:
    return {
        "level": level,
        "code": code,
        "message": VALIDATION_MESSAGES.get(code, "Cần kiểm tra thay đổi này."),
    }


def _evidence_exists(db: Session, ids: list[str]) -> bool:
    if not ids:
        return False
    count = db.scalar(
        select(func.count()).select_from(NodeEvidence).where(NodeEvidence.id.in_(ids))
    )
    return int(count or 0) == len(set(ids))


def _validate_mutation(
    db: Session, mutation: GraphMutation, proposed_node_ids: set[str]
) -> list[dict[str, str]]:
    data = mutation.proposed_json or {}
    messages: list[dict[str, str]] = []
    evidence_ids = data.get("evidence_ids") or []
    if mutation.operation in {"CREATE_NODE", "ATTACH_EVIDENCE", "CREATE_EDGE"}:
        if not _evidence_exists(db, evidence_ids):
            messages.append(
                _message("error", "EVIDENCE_REQUIRED", "Grounded source evidence is required")
            )

    if mutation.operation == "CREATE_NODE":
        label = str(data.get("canonical_label") or "").strip()
        node_type = str(data.get("node_type") or "").strip()
        parent_id = data.get("primary_parent_id")
        if not label or len(label) > 250:
            messages.append(_message("error", "INVALID_LABEL", "Canonical label is invalid"))
        if not node_type or len(node_type) > 60:
            messages.append(_message("error", "INVALID_NODE_TYPE", "Node type is invalid"))
        if not parent_id:
            messages.append(_message("error", "PARENT_REQUIRED", "A display parent is required"))
        elif parent_id not in proposed_node_ids:
            parent = db.get(KnowledgeNode, parent_id)
            if parent is None or parent.lifecycle_status != "approved":
                messages.append(
                    _message("error", "PARENT_NOT_FOUND", "Display parent is not approved")
                )
            elif mutation.target_id:
                existing_target = db.get(KnowledgeNode, mutation.target_id)
                for error in validate_placement(
                    db, parent_id, mutation.target_id if existing_target else None
                ):
                    messages.append(_message("error", "ONTOLOGY_PLACEMENT_CONFLICT", error))
        if label and node_type:
            # Ràng buộc duy nhất (node_type, normalized_key) bao gồm cả nút đã lưu trữ, nên phải
            # báo ngay ở bước kiểm tra thay vì để lượt áp dụng thất bại mãi với lỗi xung đột.
            duplicate = db.scalar(
                select(KnowledgeNode).where(
                    KnowledgeNode.node_type == node_type,
                    KnowledgeNode.normalized_key == normalize_ontology_key(label),
                )
            )
            # Mã nút xác định theo nguồn nên lần đề xuất lại sau khi hoàn tác trùng chính mã của
            # nút đã lưu trữ; nút chỉ "thuộc" bộ này khi do chính bộ này tạo ra.
            if duplicate is not None and (
                duplicate.id != mutation.target_id
                or duplicate.created_by_ref != mutation.change_set_id
            ):
                if duplicate.lifecycle_status == "approved":
                    messages.append(
                        _message(
                            "error", "DUPLICATE_NODE_CANDIDATE", "Canonical node already exists"
                        )
                    )
                else:
                    messages.append(
                        _message(
                            "error",
                            "ARCHIVED_NODE_EXISTS",
                            "An archived node with this label exists; restore it with UPDATE_NODE",
                        )
                    )
        candidates = data.get("candidates") or []
        if candidates:
            messages.append(
                _message(
                    "warning",
                    "SIMILAR_NODE_CANDIDATE",
                    "Similar canonical nodes require explicit reviewer comparison",
                )
            )

    elif mutation.operation == "ATTACH_EVIDENCE":
        target = db.get(KnowledgeNode, mutation.target_id) if mutation.target_id else None
        if target is None or target.lifecycle_status != "approved":
            messages.append(
                _message("error", "TARGET_NOT_FOUND", "Matched canonical node is not approved")
            )

    elif mutation.operation == "CREATE_EDGE":
        source_id = data.get("source_node_id")
        target_id = data.get("target_node_id")
        edge_type = data.get("edge_type")
        visible_ids = proposed_node_ids | set(
            db.scalars(
                select(KnowledgeNode.id).where(
                    KnowledgeNode.id.in_([source_id, target_id]),
                    KnowledgeNode.lifecycle_status == "approved",
                )
            )
        )
        if source_id not in visible_ids or target_id not in visible_ids:
            messages.append(
                _message("error", "EDGE_TARGET_NOT_FOUND", "Edge endpoints must be visible")
            )
        if source_id == target_id:
            messages.append(_message("error", "SELF_LOOP", "Self-loop edges are not allowed"))
        if edge_type not in ALLOWED_EDGE_TYPES:
            messages.append(_message("error", "INVALID_EDGE_TYPE", "Edge type is not approved"))
        confidence = data.get("confidence")
        if not isinstance(confidence, int | float) or not 0 <= confidence <= 1:
            messages.append(
                _message("error", "INVALID_CONFIDENCE", "Edge confidence must be 0-1")
            )
        if data.get("requires_relation_review"):
            messages.append(
                _message(
                    "warning",
                    "RELATION_TYPE_REVIEW",
                    "The source relation was normalized to RELATED_TO and needs review",
                )
            )

    elif mutation.operation == "ADD_ALIAS":
        target = db.get(KnowledgeNode, mutation.target_id) if mutation.target_id else None
        alias = str(data.get("alias") or "").strip()
        if target is None or not alias:
            messages.append(_message("error", "INVALID_ALIAS", "Alias target/value is invalid"))
        if data.get("requires_evidence") and not _evidence_exists(
            db, data.get("evidence_ids") or []
        ):
            messages.append(
                _message("error", "EVIDENCE_REQUIRED", "Grounded alias evidence is required")
            )

    elif mutation.operation in {"UPDATE_NODE", "UPDATE_EDGE"}:
        model = KnowledgeNode if mutation.operation == "UPDATE_NODE" else KnowledgeEdge
        if mutation.target_id is None or db.get(model, mutation.target_id) is None:
            messages.append(_message("error", "TARGET_NOT_FOUND", "Update target not found"))
        if data.get("lifecycle_status") not in TARGET_LIFECYCLE_STATUSES:
            messages.append(
                _message(
                    "error", "INVALID_LIFECYCLE_STATUS", "Lifecycle status must be a known state"
                )
            )
    else:
        messages.append(
            _message("error", "UNSUPPORTED_MUTATION", "Mutation operation is not supported")
        )
    return messages


def validate_change_set(
    db: Session, item: GraphChangeSet, *, commit: bool = True
) -> GraphChangeSet:
    # Bộ đã duyệt vẫn được kiểm tra lại ngay trước khi áp dụng nhưng không bị đưa ngược về
    # nháp; các trạng thái kết thúc khác giữ nguyên.
    if item.lifecycle_status not in EDITABLE_STATUSES | {"approved"}:
        return item
    mutations = change_set_mutations(db, item.id)
    proposed_node_ids = {
        mutation.target_id
        for mutation in mutations
        if mutation.operation == "CREATE_NODE"
        and mutation.target_id
        and mutation.review_decision != "rejected"
    }
    for mutation in mutations:
        if mutation.review_decision == "rejected":
            mutation.validation_status = "skipped"
            mutation.validation_messages = []
            continue
        messages = _validate_mutation(db, mutation, proposed_node_ids)
        mutation.validation_status = (
            "error"
            if any(message["level"] == "error" for message in messages)
            else "warning"
            if messages
            else "valid"
        )
        mutation.validation_messages = messages

    create_by_id = {
        mutation.target_id: mutation
        for mutation in mutations
        if mutation.operation == "CREATE_NODE"
        and mutation.target_id
        and mutation.review_decision != "rejected"
    }
    for node_id, mutation in create_by_id.items():
        visited: set[str] = set()
        current = node_id
        while current in create_by_id:
            if current in visited:
                cycle_message = _message(
                    "error", "HIERARCHY_CYCLE", "Proposed display parents contain a cycle"
                )
                if cycle_message not in mutation.validation_messages:
                    mutation.validation_messages = [
                        *mutation.validation_messages,
                        cycle_message,
                    ]
                mutation.validation_status = "error"
                break
            visited.add(current)
            current = create_by_id[current].proposed_json.get("primary_parent_id")

    active = [mutation for mutation in mutations if mutation.review_decision != "rejected"]
    error_count = sum(
        message["level"] == "error"
        for mutation in active
        for message in mutation.validation_messages
    )
    warning_count = sum(
        message["level"] == "warning"
        for mutation in active
        for message in mutation.validation_messages
    )
    valid_count = sum(
        mutation.validation_status in {"valid", "warning"} for mutation in active
    )
    item.validation_summary = {
        "mutation_count": len(mutations),
        "valid_count": valid_count,
        "error_count": error_count,
        "warning_count": warning_count,
    }
    if item.lifecycle_status in EDITABLE_STATUSES:
        item.lifecycle_status = "draft" if error_count else "needs_review"
    if commit:
        db.commit()
        db.refresh(item)
    return item


def decide_mutation(
    db: Session, item: GraphChangeSet, mutation_id: str, request: MutationDecisionRequest
) -> GraphMutation:
    item = _lock_change_set(db, item.id)
    if item.lifecycle_status not in EDITABLE_STATUSES:
        raise DocumentError(
            "CHANGE_SET_CONFLICT", "This change set is no longer editable", 409
        )
    mutation = db.get(GraphMutation, mutation_id)
    if mutation is None or mutation.change_set_id != item.id:
        raise DocumentError("MUTATION_NOT_FOUND", "Graph mutation not found", 404)
    if request.proposed_json is not None:
        if len(json.dumps(request.proposed_json)) > 20_000:
            raise DocumentError("MUTATION_TOO_LARGE", "Mutation edit is too large", 413)
        mutation.proposed_json = request.proposed_json
    mutation.review_decision = request.decision
    mutation.reviewed_by = current_actor_id()
    item.lifecycle_status = "draft"
    db.commit()
    validate_change_set(db, item)
    db.refresh(mutation)
    return mutation


def approve_change_set(db: Session, item: GraphChangeSet) -> GraphChangeSet:
    item = _lock_change_set(db, item.id)
    if item.lifecycle_status not in EDITABLE_STATUSES:
        raise DocumentError(
            "CHANGE_SET_CONFLICT", "Only draft or in-review change sets can be approved", 409
        )
    validate_change_set(db, item, commit=False)
    if item.validation_summary.get("error_count"):
        db.commit()
        raise DocumentError(
            "CHANGE_SET_CONFLICT", "Resolve validation errors before approval", 409
        )
    for mutation in change_set_mutations(db, item.id):
        if mutation.review_decision == "pending":
            mutation.review_decision = "accepted"
            mutation.reviewed_by = current_actor_id()
    item.lifecycle_status = "approved"
    item.approved_by = current_actor_id()
    db.commit()
    db.refresh(item)
    return item


def reject_change_set(db: Session, item: GraphChangeSet) -> GraphChangeSet:
    if item.lifecycle_status == "applied":
        raise DocumentError("CHANGE_SET_CONFLICT", "Applied change sets cannot be rejected", 409)
    item.lifecycle_status = "rejected"
    for mutation in change_set_mutations(db, item.id):
        if mutation.review_decision == "pending":
            mutation.review_decision = "rejected"
            mutation.reviewed_by = current_actor_id()
    db.commit()
    db.refresh(item)
    return item


def _copy_evidence(
    db: Session, evidence_ids: list[str], owner_kind: str, owner_id: str, change_set_id: str
) -> None:
    if not evidence_ids:
        return
    for source in db.scalars(select(NodeEvidence).where(NodeEvidence.id.in_(evidence_ids))):
        exists = db.scalar(
            select(NodeEvidence.id).where(
                NodeEvidence.owner_kind == owner_kind,
                NodeEvidence.owner_id == owner_id,
                NodeEvidence.content_hash == source.content_hash,
                NodeEvidence.excerpt == source.excerpt,
            )
        )
        if exists:
            continue
        db.add(
            NodeEvidence(
                owner_kind=owner_kind,
                owner_id=owner_id,
                source_document_id=source.source_document_id,
                location=source.location,
                excerpt=source.excerpt,
                content_hash=source.content_hash,
                extraction_method=source.extraction_method,
                provenance={
                    **(source.provenance or {}),
                    "change_set_id": change_set_id,
                    "source_evidence_id": source.id,
                },
            )
        )


def _apply_mutation(db: Session, item: GraphChangeSet, mutation: GraphMutation) -> None:
    data = mutation.proposed_json or {}
    if mutation.operation == "CREATE_NODE":
        existing = db.get(KnowledgeNode, mutation.target_id)
        if existing is None:
            node = KnowledgeNode(
                id=mutation.target_id,
                node_type=data["node_type"],
                canonical_label=data["canonical_label"].strip(),
                normalized_key=normalize_ontology_key(data["canonical_label"]),
                description=data.get("description", ""),
                primary_parent_id=data["primary_parent_id"],
                lifecycle_status="approved",
                created_by_type="change_set",
                created_by_ref=item.id,
                metadata_json={"source_document_node_id": data.get("source_node_id")},
            )
            db.add(node)
            db.flush()
        elif existing.created_by_ref != item.id:
            raise DocumentError("CHANGE_SET_CONFLICT", "Canonical node ID is already used", 409)
        _copy_evidence(
            db, data.get("evidence_ids", []), "knowledge_node", mutation.target_id, item.id
        )

    elif mutation.operation == "ATTACH_EVIDENCE":
        _copy_evidence(
            db, data.get("evidence_ids", []), "knowledge_node", mutation.target_id, item.id
        )

    elif mutation.operation == "CREATE_EDGE":
        existing = db.get(KnowledgeEdge, mutation.target_id)
        if existing is None:
            duplicate = db.scalar(
                select(KnowledgeEdge).where(
                    KnowledgeEdge.source_node_id == data["source_node_id"],
                    KnowledgeEdge.target_node_id == data["target_node_id"],
                    KnowledgeEdge.edge_type == data["edge_type"],
                    KnowledgeEdge.lifecycle_status == "approved",
                )
            )
            if duplicate is not None:
                raise DocumentError(
                    "CHANGE_SET_CONFLICT", "Canonical relationship already exists", 409
                )
            edge = KnowledgeEdge(
                id=mutation.target_id,
                source_node_id=data["source_node_id"],
                target_node_id=data["target_node_id"],
                edge_type=data["edge_type"],
                confidence=data["confidence"],
                lifecycle_status="approved",
                evidence_status="supported",
                created_by_type="change_set",
                created_by_ref=item.id,
                metadata_json={"source_document_edge_id": data.get("source_edge_id")},
            )
            db.add(edge)
            db.flush()
        elif existing.created_by_ref != item.id:
            raise DocumentError("CHANGE_SET_CONFLICT", "Canonical edge ID is already used", 409)
        _copy_evidence(
            db, data.get("evidence_ids", []), "knowledge_edge", mutation.target_id, item.id
        )

    elif mutation.operation == "ADD_ALIAS":
        alias = data["alias"].strip()
        db.add(
            ConceptAlias(
                knowledge_node_id=mutation.target_id,
                alias=alias,
                normalized_alias=normalize_ontology_key(alias),
                language=data.get("language", "en"),
                alias_type=data.get("alias_type", "synonym"),
                lifecycle_status="approved",
                created_by_type="change_set",
                created_by_ref=item.id,
            )
        )

    elif mutation.operation == "UPDATE_NODE":
        node = db.get(KnowledgeNode, mutation.target_id)
        mutation.before_json = {"lifecycle_status": node.lifecycle_status}
        node.lifecycle_status = data["lifecycle_status"]

    elif mutation.operation == "UPDATE_EDGE":
        edge = db.get(KnowledgeEdge, mutation.target_id)
        mutation.before_json = {"lifecycle_status": edge.lifecycle_status}
        edge.lifecycle_status = data["lifecycle_status"]


def apply_change_set(db: Session, item: GraphChangeSet) -> GraphChangeSet:
    locked = _lock_change_set(db, item.id)
    if locked.lifecycle_status == "applied":
        return locked
    if locked.lifecycle_status != "approved":
        raise DocumentError("CHANGE_SET_CONFLICT", "Change set must be approved first", 409)
    validate_change_set(db, locked, commit=False)
    if locked.validation_summary.get("error_count"):
        db.rollback()
        raise DocumentError("CHANGE_SET_CONFLICT", "Change set validation failed", 409)
    try:
        accepted = [
            mutation
            for mutation in change_set_mutations(db, locked.id)
            if mutation.review_decision == "accepted"
        ]
        for mutation in accepted:
            _apply_mutation(db, locked, mutation)
        locked.lifecycle_status = "applied"
        locked.applied_at = utcnow()
        db.add(
            AuditEvent(
                entity_type="graph_change_set",
                entity_id=locked.id,
                action="graph_change_set.applied",
                payload={"accepted_mutations": len(accepted)},
            )
        )
        if locked.origin_type == "document" and locked.origin_id:
            workspace = db.get(DocumentGraphWorkspace, locked.origin_id)
            if workspace:
                rejected = any(
                    mutation.review_decision == "rejected"
                    for mutation in change_set_mutations(db, locked.id)
                )
                workspace.review_status = "partially_merged" if rejected else "merged"
        if accepted:
            mark_canonical_graph_changed(db, reason="change_set_applied", entity_id=locked.id)
        db.commit()
        db.refresh(locked)
        return locked
    except IntegrityError as exc:
        db.rollback()
        raise DocumentError(
            "CHANGE_SET_CONFLICT", "Canonical graph changed during apply", 409
        ) from exc


def compensate_change_set(db: Session, item: GraphChangeSet) -> GraphChangeSet:
    if item.lifecycle_status != "applied":
        raise DocumentError("CHANGE_SET_CONFLICT", "Only applied change sets can be undone", 409)
    existing = db.scalar(
        select(GraphChangeSet).where(
            GraphChangeSet.origin_type == "compensation",
            GraphChangeSet.origin_id == item.id,
            GraphChangeSet.lifecycle_status.notin_({"rejected", "superseded"}),
        )
    )
    if existing:
        return existing
    compensation = GraphChangeSet(
        origin_type="compensation",
        origin_id=item.id,
        title=f"Hoàn tác: {item.title}",
        summary="Archive nodes and supersede edges created by the original change set.",
        lifecycle_status="draft",
        validation_summary={},
        created_by=current_actor_id(),
    )
    db.add(compensation)
    db.flush()
    order = 0
    for original in reversed(change_set_mutations(db, item.id)):
        if original.review_decision != "accepted":
            continue
        if original.operation == "CREATE_NODE":
            operation = "UPDATE_NODE"
            target_kind = "node"
            proposed = {"lifecycle_status": "archived"}
        elif original.operation == "CREATE_EDGE":
            operation = "UPDATE_EDGE"
            target_kind = "edge"
            proposed = {"lifecycle_status": "superseded"}
        else:
            continue
        db.add(
            GraphMutation(
                change_set_id=compensation.id,
                mutation_order=order,
                operation=operation,
                target_kind=target_kind,
                target_id=original.target_id,
                proposed_json=proposed,
                validation_status="pending",
                validation_messages=[],
                review_decision="pending",
            )
        )
        order += 1
    db.commit()
    validate_change_set(db, compensation)
    db.refresh(compensation)
    return compensation
