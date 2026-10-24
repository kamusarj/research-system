import difflib
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    ConceptAlias,
    DocumentGraphEdge,
    DocumentGraphNode,
    DocumentGraphWorkspace,
    GraphChangeSet,
    GraphMutation,
    KnowledgeNode,
    NodeEvidence,
    PaperEvaluation,
)
from app.schemas.graph_changes import OntologyCandidateRead
from app.services.object_storage import DocumentError
from app.services.ontology import ROOT_KEY, normalize_ontology_key, ontology_id

SEMANTIC_NODE_TYPES = {
    "claim": "EvidenceClaim",
    "evidence": "EvidenceClaim",
    "limitation": "Limitation",
    "method": "Method",
    "dataset": "Dataset",
    "metric": "Metric",
    "finding": "Finding",
    "concept": "Concept",
    "technology": "Technology",
    "agent_pattern": "AgentPattern",
    "business_use_case": "BusinessDomain",
    "citation": "Citation",
}
ALLOWED_EDGE_TYPES = {
    "BROADER_THAN",
    "NARROWER_THAN",
    "PARENT_OF",
    "CHILD_OF",
    "CONTAINS",
    "PART_OF",
    "RESEARCHES",
    "AUTHORED_BY",
    "COLLECTED_FROM",
    "CITES",
    "REFERENCES",
    "EXTENDS",
    "SUPPORTS",
    "CONTRADICTS",
    "REQUIRES",
    "REVIEWS",
    "IS_VERSION_OF",
    "IS_DERIVED_FROM",
    "FILLS_GAP",
    "SYNTHESIZED_INTO",
    "APPLIES_TO",
    "ACHIEVES_OUTCOME",
    "IMPLEMENTS_PATTERN",
    "HAS_CAPABILITY",
    "PERFORMS_WORKFLOW",
    "USES_TECH",
    "USES_TOOL",
    "USES_METHOD",
    "CONSUMES_DATA",
    "PRODUCES_OUTPUT",
    "EVALUATED_BY",
    "MITIGATES_RISK",
    "GOVERNED_BY",
    "DEPENDS_ON",
    "RELATED_TO",
}


def ontology_candidates(
    db: Session, label: str, node_type: str | None = None, limit: int = 5
) -> list[OntologyCandidateRead]:
    normalized = normalize_ontology_key(label)
    if not normalized:
        return []
    nodes = list(
        db.scalars(
            select(KnowledgeNode)
            .where(KnowledgeNode.lifecycle_status == "approved")
            .order_by(KnowledgeNode.canonical_label)
            .limit(500)
        )
    )
    aliases = list(
        db.execute(
            select(ConceptAlias, KnowledgeNode)
            .join(KnowledgeNode, KnowledgeNode.id == ConceptAlias.knowledge_node_id)
            .where(
                ConceptAlias.lifecycle_status == "approved",
                KnowledgeNode.lifecycle_status == "approved",
            )
            .limit(500)
        )
    )
    ranked: dict[str, OntologyCandidateRead] = {}
    for node in nodes:
        if node_type and node.node_type != node_type:
            continue
        node_key = normalize_ontology_key(node.canonical_label)
        score = 1.0 if node_key == normalized else difflib.SequenceMatcher(
            None, normalized, node_key
        ).ratio()
        matched_by = "canonical_label" if score == 1 else "similarity"
        if score < 0.55:
            continue
        ranked[node.id] = OntologyCandidateRead(
            node_id=node.id,
            canonical_label=node.canonical_label,
            node_type=node.node_type,
            primary_parent_id=node.primary_parent_id,
            matched_by=matched_by,
            score=round(score, 4),
        )
    for alias, node in aliases:
        if node_type and node.node_type != node_type:
            continue
        alias_key = normalize_ontology_key(alias.alias)
        score = 1.0 if alias_key == normalized else difflib.SequenceMatcher(
            None, normalized, alias_key
        ).ratio()
        if score < 0.55:
            continue
        existing = ranked.get(node.id)
        candidate = OntologyCandidateRead(
            node_id=node.id,
            canonical_label=node.canonical_label,
            node_type=node.node_type,
            primary_parent_id=node.primary_parent_id,
            matched_by="alias" if score == 1 else "similarity",
            score=round(score, 4),
        )
        if existing is None or candidate.score > existing.score:
            ranked[node.id] = candidate
    return sorted(
        ranked.values(), key=lambda item: (-item.score, item.canonical_label.casefold())
    )[:limit]


def _default_parent(db: Session, workspace_id: str) -> str:
    evaluation = db.scalar(
        select(PaperEvaluation).where(PaperEvaluation.workspace_id == workspace_id)
    )
    for label in evaluation.matched_pillars if evaluation else []:
        node = db.scalar(
            select(KnowledgeNode).where(
                KnowledgeNode.lifecycle_status == "approved",
                func.lower(KnowledgeNode.canonical_label) == label.casefold(),
            )
        )
        if node is not None:
            return node.id
    return ontology_id(ROOT_KEY)


def _evidence_context(db: Session, owner_id: str) -> tuple[list[str], list[dict]]:
    evidence = list(
        db.scalars(
            select(NodeEvidence)
            .where(NodeEvidence.owner_id == owner_id)
            .order_by(NodeEvidence.created_at)
        )
    )
    return [item.id for item in evidence], [
        {
            "id": item.id,
            "excerpt": item.excerpt[:280] if item.excerpt else None,
            "location": item.location or {},
        }
        for item in evidence[:3]
    ]


def create_document_change_set(
    db: Session, workspace: DocumentGraphWorkspace
) -> GraphChangeSet:
    if workspace.processing_status != "needs_review":
        raise DocumentError(
            "DOCUMENT_STATE_CONFLICT",
            "A change set can only be created from a reviewable document",
            409,
        )
    existing = db.scalar(
        select(GraphChangeSet).where(
            GraphChangeSet.origin_type == "document",
            GraphChangeSet.origin_id == workspace.id,
            GraphChangeSet.lifecycle_status.notin_({"rejected", "superseded"}),
        )
    )
    if existing is not None:
        return existing
    document_nodes = list(
        db.scalars(
            select(DocumentGraphNode)
            .where(
                DocumentGraphNode.workspace_id == workspace.id,
                DocumentGraphNode.node_type.in_(SEMANTIC_NODE_TYPES),
            )
            .order_by(DocumentGraphNode.created_at)
        )
    )
    if not document_nodes:
        raise DocumentError(
            "DOCUMENT_GRAPH_NOT_READY", "The document has no semantic graph nodes", 409
        )
    change_set = GraphChangeSet(
        origin_type="document",
        origin_id=workspace.id,
        title="Ánh xạ tri thức tài liệu vào đồ thị chuẩn",
        summary=f"Review {len(document_nodes)} semantic nodes from document workspace.",
        lifecycle_status="draft",
        validation_summary={},
        created_by="document-mapping-v1",
    )
    db.add(change_set)
    db.flush()
    default_parent_id = _default_parent(db, workspace.id)
    canonical_by_document: dict[str, str] = {}
    canonical_labels: dict[str, str] = {}
    order = 0
    for source in document_nodes:
        node_type = SEMANTIC_NODE_TYPES[source.node_type]
        candidates = ontology_candidates(db, source.label, node_type=node_type)
        exact = next((item for item in candidates if item.score == 1), None)
        evidence_ids, evidence_preview = _evidence_context(db, source.id)
        if exact:
            target_id = exact.node_id
            operation = "ATTACH_EVIDENCE"
            proposed = {
                "action": "MATCH_EXISTING",
                "source_node_id": source.id,
                "source_label": source.label,
                "target_node_id": target_id,
                "target_label": exact.canonical_label,
                "evidence_ids": evidence_ids,
                "evidence_preview": evidence_preview,
                "candidates": [item.model_dump() for item in candidates],
            }
        else:
            target_id = str(uuid.uuid4())
            operation = "CREATE_NODE"
            proposed = {
                "action": "CREATE_NEW" if not candidates else "RELATED_BUT_DISTINCT",
                "source_node_id": source.id,
                "canonical_label": source.label,
                "node_type": node_type,
                "normalized_key": normalize_ontology_key(source.label),
                "description": source.summary,
                "primary_parent_id": default_parent_id,
                "confidence": source.confidence,
                "evidence_ids": evidence_ids,
                "evidence_preview": evidence_preview,
                "candidates": [item.model_dump() for item in candidates],
            }
        canonical_by_document[source.id] = target_id
        canonical_labels[target_id] = exact.canonical_label if exact else source.label
        evidence_ids, evidence_preview = _evidence_context(db, source.id)
        db.add(
            GraphMutation(
                change_set_id=change_set.id,
                mutation_order=order,
                operation=operation,
                target_kind="node",
                target_id=target_id,
                proposed_json=proposed,
                validation_status="pending",
                validation_messages=[],
                review_decision="pending",
            )
        )
        order += 1

    document_edges = list(
        db.scalars(
            select(DocumentGraphEdge)
            .where(DocumentGraphEdge.workspace_id == workspace.id)
            .order_by(DocumentGraphEdge.created_at)
        )
    )
    for source in document_edges:
        canonical_source = canonical_by_document.get(source.source_node_id)
        canonical_target = canonical_by_document.get(source.target_node_id)
        if canonical_source is None or canonical_target is None:
            continue
        proposed_type = source.edge_type.upper().replace(" ", "_").replace("-", "_")
        mapped_type = proposed_type if proposed_type in ALLOWED_EDGE_TYPES else "RELATED_TO"
        db.add(
            GraphMutation(
                change_set_id=change_set.id,
                mutation_order=order,
                operation="CREATE_EDGE",
                target_kind="edge",
                target_id=str(uuid.uuid4()),
                proposed_json={
                    "source_edge_id": source.id,
                    "source_node_id": canonical_source,
                    "target_node_id": canonical_target,
                    "source_label": canonical_labels[canonical_source],
                    "target_label": canonical_labels[canonical_target],
                    "edge_type": mapped_type,
                    "original_edge_type": source.edge_type,
                    "confidence": source.confidence,
                    "evidence_status": source.evidence_status,
                    "evidence_ids": evidence_ids,
                    "evidence_preview": evidence_preview,
                    "requires_relation_review": mapped_type != proposed_type,
                },
                validation_status="pending",
                validation_messages=[],
                review_decision="pending",
            )
        )
        order += 1
    db.commit()
    db.refresh(change_set)
    return change_set
