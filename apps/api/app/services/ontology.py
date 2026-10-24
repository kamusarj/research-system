import re
import unicodedata
import uuid
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import ConceptAlias, KnowledgeNode

ONTOLOGY_NAMESPACE = uuid.UUID("83f8c449-6c7b-5cdd-92e7-88c6c2d97219")
ROOT_KEY = "business-ai-agents"


@dataclass(frozen=True)
class SeedNode:
    key: str
    label: str
    label_vi: str
    node_type: str
    parent_key: str | None = ROOT_KEY


SEED_NODES = (
    SeedNode(ROOT_KEY, "Business AI Agents", "Business AI Agents", "SystemRoot", None),
    SeedNode(
        "business-problems-outcomes",
        "Business Problems & Outcomes",
        "Bài toán và kết quả kinh doanh",
        "SystemPillar",
    ),
    SeedNode("business-context", "Business Context", "Bối cảnh kinh doanh", "SystemPillar"),
    SeedNode(
        "agent-system-architecture",
        "Agent System Architecture",
        "Kiến trúc hệ thống agent",
        "SystemPillar",
    ),
    SeedNode(
        "agent-capabilities-workflows",
        "Agent Capabilities & Workflows",
        "Năng lực và quy trình agent",
        "SystemPillar",
    ),
    SeedNode(
        "business-methods-decision-intelligence",
        "Business Methods & Decision Intelligence",
        "Phương pháp kinh doanh và trí tuệ quyết định",
        "SystemPillar",
    ),
    SeedNode(
        "data-knowledge-memory",
        "Data, Knowledge & Memory",
        "Dữ liệu, tri thức và bộ nhớ",
        "SystemPillar",
    ),
    SeedNode(
        "tools-functions-integrations",
        "Tools, Functions & Integrations",
        "Công cụ, hàm và tích hợp",
        "SystemPillar",
    ),
    SeedNode(
        "outputs-actions-feedback",
        "Outputs, Actions & Feedback",
        "Đầu ra, hành động và phản hồi",
        "SystemPillar",
    ),
    SeedNode(
        "evaluation-risk-governance",
        "Evaluation, Risk & Governance",
        "Đánh giá, rủi ro và quản trị",
        "SystemPillar",
    ),
    SeedNode(
        "engineering-operations",
        "Engineering & Operations",
        "Kỹ thuật và vận hành",
        "SystemPillar",
    ),
    SeedNode(
        "research-evidence",
        "Research & Evidence",
        "Nghiên cứu và bằng chứng",
        "SystemPillar",
    ),
)


def ontology_id(key: str) -> str:
    return str(uuid.uuid5(ONTOLOGY_NAMESPACE, key))


def normalize_ontology_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def ensure_seed_ontology(db: Session) -> list[KnowledgeNode]:
    ids = {seed.key: ontology_id(seed.key) for seed in SEED_NODES}
    existing = set(db.scalars(select(KnowledgeNode.id).where(KnowledgeNode.id.in_(ids.values()))))
    for seed in SEED_NODES:
        node_id = ids[seed.key]
        if node_id in existing:
            continue
        db.add(
            KnowledgeNode(
                id=node_id,
                node_type=seed.node_type,
                canonical_label=seed.label,
                label_vi=seed.label_vi,
                normalized_key=seed.key,
                description=(
                    "Canonical root for the Business AI Agents knowledge system."
                    if seed.parent_key is None
                    else f"Canonical Business AI Agents pillar: {seed.label}."
                ),
                primary_parent_id=ids.get(seed.parent_key),
                lifecycle_status="approved",
                created_by_type="migration",
                created_by_ref="graph-intelligence-v2",
                metadata_json={"seed_version": "business-ai-agents-v1"},
            )
        )
    db.commit()
    return list(
        db.scalars(
            select(KnowledgeNode)
            .where(KnowledgeNode.id.in_(ids.values()))
            .order_by(KnowledgeNode.canonical_label)
        )
    )


def get_node(db: Session, node_id: str) -> KnowledgeNode:
    node = db.get(KnowledgeNode, node_id)
    if node is None:
        raise HTTPException(404, "Ontology node not found")
    return node


def child_count(db: Session, node_id: str, include_drafts: bool = False) -> int:
    statement = (
        select(func.count())
        .select_from(KnowledgeNode)
        .where(KnowledgeNode.primary_parent_id == node_id)
    )
    if not include_drafts:
        statement = statement.where(KnowledgeNode.lifecycle_status == "approved")
    return int(db.scalar(statement) or 0)


def list_children(db: Session, node_id: str, include_drafts: bool = False) -> list[KnowledgeNode]:
    get_node(db, node_id)
    statement = select(KnowledgeNode).where(KnowledgeNode.primary_parent_id == node_id)
    if not include_drafts:
        statement = statement.where(KnowledgeNode.lifecycle_status == "approved")
    return list(db.scalars(statement.order_by(KnowledgeNode.canonical_label)))


def breadcrumb(db: Session, node_id: str) -> list[KnowledgeNode]:
    current = get_node(db, node_id)
    path = [current]
    visited = {current.id}
    while current.primary_parent_id:
        if current.primary_parent_id in visited:
            raise HTTPException(409, "Ontology hierarchy contains a cycle")
        current = get_node(db, current.primary_parent_id)
        path.append(current)
        visited.add(current.id)
    return list(reversed(path))


def validate_placement(db: Session, parent_id: str, node_id: str | None = None) -> list[str]:
    errors: list[str] = []
    get_node(db, parent_id)
    if node_id is None:
        return errors
    get_node(db, node_id)
    if node_id == parent_id:
        return ["A node cannot be its own parent"]
    current_id: str | None = parent_id
    visited: set[str] = set()
    while current_id:
        if current_id == node_id:
            errors.append("Placement would create a hierarchy cycle")
            break
        if current_id in visited:
            errors.append("Existing ontology hierarchy contains a cycle")
            break
        visited.add(current_id)
        current = get_node(db, current_id)
        current_id = current.primary_parent_id
    return errors


def search_nodes(db: Session, query: str, limit: int = 20) -> list[KnowledgeNode]:
    needle = f"%{query.casefold().strip()}%"
    alias_node_ids = select(ConceptAlias.knowledge_node_id).where(
        func.lower(ConceptAlias.alias).like(needle), ConceptAlias.lifecycle_status == "approved"
    )
    statement = (
        select(KnowledgeNode)
        .where(
            KnowledgeNode.lifecycle_status == "approved",
            or_(
                func.lower(KnowledgeNode.canonical_label).like(needle),
                func.lower(func.coalesce(KnowledgeNode.label_vi, "")).like(needle),
                KnowledgeNode.id.in_(alias_node_ids),
            ),
        )
        .order_by(KnowledgeNode.canonical_label)
        .limit(limit)
    )
    return list(db.scalars(statement))
