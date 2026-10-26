from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.identity import (
    Principal,
    current_actor_id,
    current_principal,
    current_principal_may_publish,
)
from app.models import (
    AuditEvent,
    DocumentGraphWorkspace,
    IntakeReceipt,
    IntakeReceiptItem,
    KnowledgeGap,
    LinkSubmission,
    Tag,
    research_tags,
    utcnow,
)
from app.schemas.ingestion import LinkCreate
from app.schemas.intake_receipts import (
    KnowledgeGapSummary,
    ReceiptCreate,
    ReceiptItemRead,
    ReceiptRead,
)
from app.services.chatgpt_plan import PROVIDER_ID as PLAN_PROVIDER_ID
from app.services.chatgpt_plan import default_provider_for
from app.services.documents import (
    add_document_records,
    normalized_upload,
    validated_upload_chunks,
)
from app.services.object_storage import DocumentError, ObjectStorage, StoredObject
from app.services.sources import normalize_url


@dataclass(frozen=True, slots=True)
class ReceiptDelivery:
    receipt: IntakeReceipt
    dispositions: dict[str, str]
    replayed: bool


MAX_RECEIPT_GAP_ALERTS = 10
ALERTABLE_GAP_STATUSES = ("detected", "prioritized", "assigned")


def _hash(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode()).hexdigest()


def delivery_key(source_type: str, source_namespace: str, occurrence_ref: str) -> str:
    return _hash("receipt-v1", source_type, source_namespace, occurrence_ref)


def url_item_key(normalized_url: str) -> str:
    return _hash("url-v1", normalized_url)


def document_item_key(external_item_ref: str, content_sha256: str) -> str:
    return _hash("document-v1", external_item_ref, content_sha256)


def _fallback_principal() -> Principal:
    return Principal(
        id=current_actor_id(),
        name="Chủ sở hữu cục bộ",
        email="local@research.invalid",
        role="owner",
        auth_kind="local",
    )


def _actor(principal: Principal | None) -> Principal:
    return principal or current_principal() or _fallback_principal()


def _authorize_namespace(principal: Principal, namespace: str) -> None:
    if principal.auth_kind == "service" and principal.source_namespace != namespace:
        raise DocumentError(
            "ACCESS_DENIED", "The service account cannot access this receipt namespace", 403
        )


def _source_metadata(data: ReceiptCreate) -> dict[str, object]:
    return data.source.metadata.model_dump(mode="json", exclude_none=True)


def _requested_provider(db: Session, data, principal: Principal) -> str:
    # Tài khoản dịch vụ (Discord…) không có gói ChatGPT riêng: luôn theo cấu hình máy chủ.
    preferred = None if principal.auth_kind == "service" else default_provider_for(db, principal.id)
    return data.provider or preferred or settings.ai_provider


def _new_submission(
    db: Session,
    *,
    url: str,
    data,
    source_type: str,
    source_ref: str,
    principal: Principal,
) -> LinkSubmission:
    return LinkSubmission(
        url=url,
        source_type=source_type,
        source_ref=source_ref,
        submitted_by=principal.id,
        provider_name=_requested_provider(db, data, principal),
        auto_approve=data.auto_approve and current_principal_may_publish(),
        status="pending",
        stage="pending",
        next_attempt_at=utcnow(),
    )


def _deliver_urls_once(db: Session, data: ReceiptCreate, principal: Principal) -> ReceiptDelivery:
    source = data.source
    _authorize_namespace(principal, source.namespace)
    key = delivery_key(source.type, source.namespace, source.occurrence_ref)
    receipt = db.scalar(
        select(IntakeReceipt).where(IntakeReceipt.delivery_key_hash == key).with_for_update()
    )
    now = utcnow()
    existed = receipt is not None
    if receipt is None:
        receipt = IntakeReceipt(
            source_type=source.type,
            source_namespace=source.namespace,
            external_occurrence_ref=source.occurrence_ref,
            delivery_key_hash=key,
            container_ref=source.container_ref,
            submitted_by=principal.id,
            external_actor_ref_hash=(
                _hash(source.external_actor_ref) if source.external_actor_ref else None
            ),
            metadata_json=_source_metadata(data),
            delivery_count=1,
            received_at=now,
            last_seen_at=now,
        )
        db.add(receipt)
        db.flush()
    else:
        if (
            receipt.source_type != source.type
            or receipt.source_namespace != source.namespace
            or receipt.external_occurrence_ref != source.occurrence_ref
            or (
                receipt.container_ref is not None
                and source.container_ref is not None
                and receipt.container_ref != source.container_ref
            )
        ):
            raise DocumentError(
                "SOURCE_OCCURRENCE_CONFLICT",
                "The source occurrence identity conflicts with an existing receipt",
                409,
            )
        if receipt.container_ref is None and source.container_ref is not None:
            receipt.container_ref = source.container_ref
        receipt.delivery_count += 1
        receipt.last_seen_at = now

    existing_items = {
        item.item_key_hash: item
        for item in db.scalars(
            select(IntakeReceiptItem).where(IntakeReceiptItem.receipt_id == receipt.id)
        )
    }
    next_ordinal = max((item.ordinal for item in existing_items.values()), default=0) + 1
    dispositions: dict[str, str] = {}
    seen_keys: set[str] = set()
    created_count = 0
    for requested in data.items:
        normalized = normalize_url(str(requested.url))
        item_key = url_item_key(normalized)
        if item_key in seen_keys:
            continue
        seen_keys.add(item_key)
        existing_item = existing_items.get(item_key)
        if existing_item is not None:
            dispositions[existing_item.id] = "replayed"
            continue

        submission = db.scalar(
            select(LinkSubmission).where(LinkSubmission.url == normalized).with_for_update()
        )
        initial_disposition = "linked_existing"
        if submission is not None and _should_requeue(submission):
            _reset_failed_submission(db, submission, requested, principal)
            initial_disposition = "queued"
        elif submission is None:
            submission = _new_submission(
                db,
                url=normalized,
                data=requested,
                source_type=source.type,
                source_ref=source.occurrence_ref,
                principal=principal,
            )
            db.add(submission)
            db.flush()
            initial_disposition = "queued"
        item = IntakeReceiptItem(
            receipt_id=receipt.id,
            ordinal=next_ordinal,
            kind="url",
            item_key_hash=item_key,
            normalized_url=normalized,
            link_submission_id=submission.id,
            initial_disposition=initial_disposition,
        )
        next_ordinal += 1
        db.add(item)
        db.flush()
        dispositions[item.id] = initial_disposition
        existing_items[item_key] = item
        created_count += 1

    counts = {
        value: list(dispositions.values()).count(value) for value in set(dispositions.values())
    }
    db.add(
        AuditEvent(
            entity_type="intake_receipt",
            entity_id=receipt.id,
            action="intake.receipt.delivered",
            actor=principal.id,
            payload={
                "source_type": receipt.source_type,
                "namespace_hash": _hash(receipt.source_namespace),
                "occurrence_ref_hash": _hash(receipt.external_occurrence_ref),
                "item_kind": "url",
                "item_count": len(dispositions),
                "new_item_count": created_count,
                "dispositions": counts,
            },
        )
    )
    db.commit()
    db.refresh(receipt)
    return ReceiptDelivery(
        receipt=receipt,
        dispositions=dispositions,
        replayed=existed and all(value == "replayed" for value in dispositions.values()),
    )


def deliver_url_receipt(
    db: Session, data: ReceiptCreate, principal: Principal | None = None
) -> ReceiptDelivery:
    actor = _actor(principal)
    for attempt in range(2):
        try:
            return _deliver_urls_once(db, data, actor)
        except IntegrityError as exc:
            db.rollback()
            if attempt:
                raise DocumentError(
                    "SOURCE_OCCURRENCE_CONFLICT",
                    "The intake receipt could not be created consistently",
                    409,
                ) from exc
    raise AssertionError("unreachable")


def _should_requeue(item: LinkSubmission) -> bool:
    # Gửi lại một liên kết đã thất bại, hoặc bản trùng của nguồn gốc chưa được xuất bản (ví dụ
    # nguồn gốc đã bị từ chối), phải xử lý lại từ đầu thay vì trả về mãi kết cục cũ.
    return item.status == "failed" or (
        item.review_status == "duplicate" and item.research_id is None
    )


def _reset_failed_submission(
    db: Session, item: LinkSubmission, data: LinkCreate, principal: Principal
) -> None:
    item.status = "pending"
    item.stage = "pending"
    item.review_status = "not_requested"
    item.duplicate_of_id = None
    item.attempt_count = 0
    item.next_attempt_at = utcnow()
    item.started_at = None
    item.finished_at = None
    item.error = None
    item.error_code = None
    item.error_details = {}
    item.provider_name = _requested_provider(db, data, principal)
    if item.provider_name == PLAN_PROVIDER_ID:
        # Người gửi lại link chạy bằng gói ChatGPT của chính họ, nên họ là người được tính quota.
        item.submitted_by = principal.id
    item.auto_approve = data.auto_approve and current_principal_may_publish()


def create_compatibility_submission(
    db: Session, data: LinkCreate, principal: Principal | None = None
) -> tuple[LinkSubmission, bool, ReceiptDelivery]:
    actor = _actor(principal)
    normalized = normalize_url(str(data.url))
    existing = db.scalar(select(LinkSubmission).where(LinkSubmission.url == normalized))
    requeued = existing is not None and _should_requeue(existing)
    if requeued:
        _reset_failed_submission(db, existing, data, actor)
    occurrence_ref = data.source_ref or str(uuid.uuid4())
    namespace = "local" if data.source_type == "manual" else f"compat-{data.source_type}"
    receipt_data = ReceiptCreate.model_validate(
        {
            "source": {
                "type": data.source_type,
                "namespace": namespace,
                "occurrence_ref": occurrence_ref,
                "metadata": {
                    "schema_version": 1,
                    "event_type": (
                        "manual_submit" if data.source_type == "manual" else "api_request"
                    ),
                },
            },
            "items": [
                {
                    "kind": "url",
                    "url": normalized,
                    "provider": data.provider,
                    "auto_approve": data.auto_approve,
                }
            ],
        }
    )
    delivery = deliver_url_receipt(db, receipt_data, actor)
    item = next(db.get(IntakeReceiptItem, item_id) for item_id in delivery.dispositions)
    submission = db.get(LinkSubmission, item.link_submission_id)
    if submission is None:
        raise DocumentError("INTERNAL_ERROR", "Receipt processing link is unavailable", 500)
    return submission, existing is not None and not requeued, delivery


async def _verify_stored(storage: ObjectStorage, stored: StoredObject) -> None:
    digest = hashlib.sha256()
    size = 0
    async for chunk in storage.open(stored.key):
        size += len(chunk)
        digest.update(chunk)
    if size != stored.size_bytes or digest.hexdigest() != stored.sha256:
        raise DocumentError("DOCUMENT_STORAGE_FAILED", "Stored document verification failed", 503)


async def deliver_document_item(
    db: Session,
    receipt_id: str,
    upload: UploadFile,
    external_item_ref: str,
    storage: ObjectStorage,
    *,
    provider_name: str | None = None,
    principal: Principal | None = None,
) -> ReceiptDelivery:
    actor = _actor(principal)
    receipt = db.get(IntakeReceipt, receipt_id)
    if receipt is None:
        raise DocumentError("SOURCE_NOT_FOUND", "Intake receipt not found", 404)
    _authorize_namespace(actor, receipt.source_namespace)
    external_ref = external_item_ref.strip()
    if not external_ref or len(external_ref) > 500 or any(ord(char) < 32 for char in external_ref):
        raise DocumentError("INVALID_REQUEST", "Document item reference is invalid", 422)

    filename, suffix, mime_type = normalized_upload(upload.filename, upload.content_type)
    workspace_id = str(uuid.uuid4())
    object_key = f"documents/{workspace_id}/{uuid.uuid4().hex}{suffix}"
    stored = await storage.put(
        object_key,
        validated_upload_chunks(upload, suffix),
        {"filename": filename, "mime_type": mime_type},
    )
    retained_object = True
    try:
        await _verify_stored(storage, stored)
        existing_item = db.scalar(
            select(IntakeReceiptItem).where(
                IntakeReceiptItem.receipt_id == receipt.id,
                IntakeReceiptItem.kind == "document",
                IntakeReceiptItem.external_item_ref == external_ref,
            )
        )
        if existing_item is not None:
            await storage.delete(stored.key)
            retained_object = False
            if existing_item.content_sha256 != stored.sha256:
                raise DocumentError(
                    "SOURCE_ITEM_CONFLICT",
                    "The document item reference was reused with different bytes",
                    409,
                )
            receipt.delivery_count += 1
            receipt.last_seen_at = utcnow()
            _add_receipt_audit(db, receipt, actor.id, "document", {"replayed": 1})
            db.commit()
            db.refresh(receipt)
            return ReceiptDelivery(receipt, {existing_item.id: "replayed"}, True)

        duplicate = db.scalar(
            select(DocumentGraphWorkspace).where(
                DocumentGraphWorkspace.content_hash == stored.sha256
            )
        )
        initial_disposition = "linked_existing"
        if duplicate is None:
            workspace = add_document_records(
                db,
                filename=filename,
                mime_type=mime_type,
                workspace_id=workspace_id,
                stored=stored,
                provider_name=provider_name,
            )
            initial_disposition = "queued"
        else:
            workspace = duplicate
            await storage.delete(stored.key)
            retained_object = False

        next_ordinal = (
            int(
                db.scalar(
                    select(func.coalesce(func.max(IntakeReceiptItem.ordinal), 0)).where(
                        IntakeReceiptItem.receipt_id == receipt.id
                    )
                )
                or 0
            )
            + 1
        )
        item = IntakeReceiptItem(
            receipt_id=receipt.id,
            ordinal=next_ordinal,
            kind="document",
            item_key_hash=document_item_key(external_ref, stored.sha256),
            external_item_ref=external_ref,
            content_sha256=stored.sha256,
            document_workspace_id=workspace.id,
            initial_disposition=initial_disposition,
        )
        db.add(item)
        db.flush()
        receipt.delivery_count += 1
        receipt.last_seen_at = utcnow()
        _add_receipt_audit(db, receipt, actor.id, "document", {initial_disposition: 1})
        db.commit()
        db.refresh(receipt)
        return ReceiptDelivery(receipt, {item.id: initial_disposition}, False)
    except DocumentError:
        db.rollback()
        if retained_object:
            await storage.delete(stored.key)
        raise
    except IntegrityError as exc:
        db.rollback()
        if retained_object:
            await storage.delete(stored.key)
        existing_item = db.scalar(
            select(IntakeReceiptItem).where(
                IntakeReceiptItem.receipt_id == receipt_id,
                IntakeReceiptItem.kind == "document",
                IntakeReceiptItem.external_item_ref == external_ref,
            )
        )
        if existing_item is not None and existing_item.content_sha256 == stored.sha256:
            receipt = db.get(IntakeReceipt, receipt_id)
            if receipt is None:
                raise DocumentError("SOURCE_NOT_FOUND", "Intake receipt not found", 404) from exc
            receipt.delivery_count += 1
            receipt.last_seen_at = utcnow()
            _add_receipt_audit(db, receipt, actor.id, "document", {"replayed": 1})
            db.commit()
            db.refresh(receipt)
            return ReceiptDelivery(receipt, {existing_item.id: "replayed"}, True)
        raise DocumentError(
            "SOURCE_ITEM_CONFLICT", "The document item could not be linked consistently", 409
        ) from exc
    except Exception:
        db.rollback()
        if retained_object:
            await storage.delete(stored.key)
        raise


def _add_receipt_audit(
    db: Session,
    receipt: IntakeReceipt,
    actor_id: str,
    item_kind: str,
    dispositions: dict[str, int],
) -> None:
    db.add(
        AuditEvent(
            entity_type="intake_receipt",
            entity_id=receipt.id,
            action="intake.receipt.delivered",
            actor=actor_id,
            payload={
                "source_type": receipt.source_type,
                "namespace_hash": _hash(receipt.source_namespace),
                "occurrence_ref_hash": _hash(receipt.external_occurrence_ref),
                "item_kind": item_kind,
                "item_count": sum(dispositions.values()),
                "dispositions": dispositions,
            },
        )
    )


def _related_gap_summaries(db: Session, research_id: str | None) -> list[KnowledgeGapSummary]:
    """Return only active gaps supported by tags on this receipt item's research.

    The receipt read is already namespace-confined. Keeping this projection tied to the
    linked research item prevents a service account from using it as a general gap-list
    endpoint, while the limit keeps one unusually broad classification from producing an
    unbounded platform reply.
    """

    if research_id is None:
        return []
    gaps = db.scalars(
        select(KnowledgeGap)
        .join(Tag, Tag.name == KnowledgeGap.concept_key)
        .join(research_tags, research_tags.c.tag_id == Tag.id)
        .where(
            research_tags.c.research_id == research_id,
            KnowledgeGap.status.in_(ALERTABLE_GAP_STATUSES),
        )
        .order_by(KnowledgeGap.priority.desc(), KnowledgeGap.updated_at.desc())
        .limit(MAX_RECEIPT_GAP_ALERTS)
    )
    return [
        KnowledgeGapSummary(
            id=gap.id,
            title=gap.title,
            concept_key=gap.concept_key,
            status=gap.status,
            priority=gap.priority,
            coverage_count=gap.coverage_count,
            reason=gap.reason,
        )
        for gap in gaps
    ]


def _item_projection(
    db: Session, item: IntakeReceiptItem, disposition: str
) -> tuple[ReceiptItemRead, str]:
    if item.link_submission_id is not None:
        target = db.get(LinkSubmission, item.link_submission_id)
        if target is None:
            raise DocumentError("INTERNAL_ERROR", "Receipt URL job is unavailable", 500)
        if target.status == "pending":
            projected = "queued"
        elif target.status in {"processing", "fetching", "extracting", "analyzing"}:
            projected = "processing"
        elif target.status == "failed":
            projected = "failed"
        elif target.review_status == "approved":
            projected = "approved"
        elif target.review_status in {"duplicate", "rejected"}:
            # Không còn chờ ai duyệt: báo đúng kết cục thay vì "đang chờ duyệt" mãi.
            projected = target.review_status
        elif target.status == "partial_success":
            projected = "partial_success"
        else:
            projected = "needs_review"
        return (
            ReceiptItemRead(
                id=item.id,
                ordinal=item.ordinal,
                kind="url",
                disposition=disposition,
                initial_disposition=item.initial_disposition,
                normalized_url=item.normalized_url,
                link_submission_id=target.id,
                status=target.status,
                review_status=target.review_status,
                research_id=target.research_id,
                error_code=target.error_code,
                knowledge_gaps=_related_gap_summaries(db, target.research_id),
            ),
            projected,
        )

    workspace = db.get(DocumentGraphWorkspace, item.document_workspace_id)
    if workspace is None:
        raise DocumentError("INTERNAL_ERROR", "Receipt document workspace is unavailable", 500)
    if workspace.processing_status in {"uploaded", "queued"}:
        projected = "queued"
    elif workspace.processing_status in {
        "processing",
        "extracting",
        "evaluating",
        "graph_building",
    }:
        projected = "processing"
    elif workspace.processing_status == "failed":
        projected = "failed"
    elif workspace.review_status == "approved":
        projected = "approved"
    elif workspace.processing_status == "partial_success":
        projected = "partial_success"
    else:
        projected = "needs_review"
    return (
        ReceiptItemRead(
            id=item.id,
            ordinal=item.ordinal,
            kind="document",
            disposition=disposition,
            initial_disposition=item.initial_disposition,
            document_workspace_id=workspace.id,
            status=workspace.processing_status,
            review_status=workspace.review_status,
            research_id=workspace.research_id,
            error_code=workspace.error_code,
            knowledge_gaps=_related_gap_summaries(db, workspace.research_id),
        ),
        projected,
    )


def serialize_receipt(
    db: Session,
    delivery: ReceiptDelivery,
    principal: Principal | None = None,
) -> ReceiptRead:
    actor = _actor(principal)
    receipt = delivery.receipt
    _authorize_namespace(actor, receipt.source_namespace)
    stored_items = list(
        db.scalars(
            select(IntakeReceiptItem)
            .where(IntakeReceiptItem.receipt_id == receipt.id)
            .order_by(IntakeReceiptItem.ordinal)
        )
    )
    reads: list[ReceiptItemRead] = []
    projected: list[str] = []
    for item in stored_items:
        read, state = _item_projection(
            db,
            item,
            delivery.dispositions.get(item.id, item.initial_disposition),
        )
        reads.append(read)
        projected.append(state)
    if not projected:
        aggregate = "queued"
    elif "processing" in projected:
        aggregate = "processing"
    elif "queued" in projected:
        aggregate = "queued"
    elif len(set(projected)) == 1:
        aggregate = projected[0]
    else:
        aggregate = "mixed"
    return ReceiptRead(
        id=receipt.id,
        source_type=receipt.source_type,
        source_namespace=receipt.source_namespace,
        external_occurrence_ref=receipt.external_occurrence_ref,
        container_ref=receipt.container_ref,
        replayed=delivery.replayed,
        status=aggregate,
        delivery_count=receipt.delivery_count,
        received_at=receipt.received_at,
        last_seen_at=receipt.last_seen_at,
        items=reads,
    )


def find_receipt_by_occurrence(
    db: Session, occurrence_ref: str, principal: Principal | None = None
) -> ReceiptDelivery:
    """Look a receipt up by the reference the calling system already has.

    A Discord user has a message ID, not a receipt ID. The lookup is still confined to the
    caller's own namespace, so one gateway cannot read another's intake by guessing refs.
    """

    actor = _actor(principal)
    namespace = getattr(actor, "source_namespace", None)
    statement = select(IntakeReceipt).where(IntakeReceipt.external_occurrence_ref == occurrence_ref)
    if namespace:
        statement = statement.where(IntakeReceipt.source_namespace == namespace)
    receipt = db.scalar(statement.order_by(IntakeReceipt.received_at.desc()))
    if receipt is None:
        raise DocumentError("SOURCE_NOT_FOUND", "Intake receipt not found", 404)
    _authorize_namespace(actor, receipt.source_namespace)
    return ReceiptDelivery(receipt, {}, False)


def get_receipt_delivery(
    db: Session, receipt_id: str, principal: Principal | None = None
) -> ReceiptDelivery:
    actor = _actor(principal)
    receipt = db.get(IntakeReceipt, receipt_id)
    if receipt is None:
        raise DocumentError("SOURCE_NOT_FOUND", "Intake receipt not found", 404)
    _authorize_namespace(actor, receipt.source_namespace)
    return ReceiptDelivery(receipt, {}, False)
