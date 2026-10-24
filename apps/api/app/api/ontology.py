from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import KnowledgeNode
from app.schemas.graph_changes import OntologyCandidateRead
from app.schemas.ontology import (
    OntologyEdgeRead,
    OntologyNodeRead,
    OntologyTreeRead,
    PlacementValidationRead,
    PlacementValidationRequest,
)
from app.services.ontology import (
    breadcrumb,
    child_count,
    get_node,
    list_children,
    search_nodes,
    validate_placement,
)
from app.services.ontology_mapping import ontology_candidates

router = APIRouter(prefix="/ontology", tags=["ontology"])


def serialize_node(db: Session, node: KnowledgeNode) -> OntologyNodeRead:
    return OntologyNodeRead(
        id=node.id,
        node_type=node.node_type,
        canonical_label=node.canonical_label,
        label_vi=node.label_vi,
        normalized_key=node.normalized_key,
        description=node.description,
        scope_note=node.scope_note,
        primary_parent_id=node.primary_parent_id,
        child_count=child_count(db, node.id),
        lifecycle_status=node.lifecycle_status,
        created_at=node.created_at,
        updated_at=node.updated_at,
    )


@router.get("", response_model=OntologyTreeRead)
def ontology(db: Session = Depends(get_db)) -> OntologyTreeRead:
    nodes = list(
        db.scalars(
            select(KnowledgeNode)
            .where(KnowledgeNode.lifecycle_status == "approved")
            .order_by(KnowledgeNode.canonical_label)
        )
    )
    node_ids = {node.id for node in nodes}
    edges = [
        OntologyEdgeRead(
            id=f"hierarchy:{node.primary_parent_id}:{node.id}",
            source=node.primary_parent_id,
            target=node.id,
        )
        for node in nodes
        if node.primary_parent_id in node_ids
    ]
    return OntologyTreeRead(
        nodes=[serialize_node(db, node) for node in nodes],
        edges=edges,
        root_ids=[node.id for node in nodes if node.primary_parent_id is None],
    )


@router.get("/roots", response_model=list[OntologyNodeRead])
def roots(db: Session = Depends(get_db)) -> list[OntologyNodeRead]:
    items = list(
        db.scalars(
            select(KnowledgeNode)
            .where(
                KnowledgeNode.lifecycle_status == "approved",
                KnowledgeNode.primary_parent_id.is_(None),
            )
            .order_by(KnowledgeNode.canonical_label)
        )
    )
    return [serialize_node(db, item) for item in items]


@router.get("/nodes/{node_id}", response_model=OntologyNodeRead)
def node(node_id: str, db: Session = Depends(get_db)) -> OntologyNodeRead:
    return serialize_node(db, get_node(db, node_id))


@router.get("/nodes/{node_id}/breadcrumb", response_model=list[OntologyNodeRead])
def node_breadcrumb(node_id: str, db: Session = Depends(get_db)) -> list[OntologyNodeRead]:
    return [serialize_node(db, item) for item in breadcrumb(db, node_id)]


@router.get("/nodes/{node_id}/children", response_model=list[OntologyNodeRead])
def children(
    node_id: str,
    include_drafts: bool = False,
    db: Session = Depends(get_db),
) -> list[OntologyNodeRead]:
    return [serialize_node(db, child) for child in list_children(db, node_id, include_drafts)]


@router.get("/search", response_model=list[OntologyNodeRead])
def search(
    q: str = Query(min_length=1, max_length=250),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[OntologyNodeRead]:
    return [serialize_node(db, item) for item in search_nodes(db, q, limit)]


@router.get("/candidates", response_model=list[OntologyCandidateRead])
def candidates(
    q: str = Query(min_length=1, max_length=250),
    node_type: str | None = Query(default=None, max_length=60),
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
) -> list[OntologyCandidateRead]:
    return ontology_candidates(db, q, node_type, limit)


@router.post("/validate-placement", response_model=PlacementValidationRead)
def placement(
    data: PlacementValidationRequest, db: Session = Depends(get_db)
) -> PlacementValidationRead:
    errors = validate_placement(db, data.parent_id, data.node_id)
    return PlacementValidationRead(
        valid=not errors,
        errors=errors,
        breadcrumb=[serialize_node(db, item) for item in breadcrumb(db, data.parent_id)],
    )
