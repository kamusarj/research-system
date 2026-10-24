from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import GraphChangeSet
from app.schemas.graph_changes import (
    GraphChangeSetList,
    GraphChangeSetRead,
    GraphMutationRead,
    MutationDecisionRequest,
)
from app.services.graph_changes import (
    apply_change_set,
    approve_change_set,
    compensate_change_set,
    decide_mutation,
    get_change_set,
    reject_change_set,
    serialize_change_set,
    serialize_mutation,
    validate_change_set,
)

router = APIRouter(prefix="/graph/change-sets", tags=["graph-change-sets"])


@router.get("", response_model=GraphChangeSetList)
def list_change_sets(
    status: str | None = Query(default=None, max_length=30),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> GraphChangeSetList:
    statement = select(GraphChangeSet).order_by(GraphChangeSet.created_at.desc()).limit(limit)
    count_statement = select(func.count()).select_from(GraphChangeSet)
    if status:
        statement = statement.where(GraphChangeSet.lifecycle_status == status)
        count_statement = count_statement.where(GraphChangeSet.lifecycle_status == status)
    items = list(db.scalars(statement))
    return GraphChangeSetList(
        items=[serialize_change_set(db, item) for item in items],
        total=int(db.scalar(count_statement) or 0),
    )


@router.get("/{change_set_id}", response_model=GraphChangeSetRead)
def change_set(change_set_id: str, db: Session = Depends(get_db)) -> GraphChangeSetRead:
    return serialize_change_set(db, get_change_set(db, change_set_id))


@router.post("/{change_set_id}/validate", response_model=GraphChangeSetRead)
def validate(change_set_id: str, db: Session = Depends(get_db)) -> GraphChangeSetRead:
    item = validate_change_set(db, get_change_set(db, change_set_id))
    return serialize_change_set(db, item)


@router.post(
    "/{change_set_id}/mutations/{mutation_id}/decision",
    response_model=GraphMutationRead,
)
def mutation_decision(
    change_set_id: str,
    mutation_id: str,
    request: MutationDecisionRequest,
    db: Session = Depends(get_db),
) -> GraphMutationRead:
    item = get_change_set(db, change_set_id)
    return serialize_mutation(decide_mutation(db, item, mutation_id, request))


@router.post("/{change_set_id}/approve", response_model=GraphChangeSetRead)
def approve(change_set_id: str, db: Session = Depends(get_db)) -> GraphChangeSetRead:
    item = approve_change_set(db, get_change_set(db, change_set_id))
    return serialize_change_set(db, item)


@router.post("/{change_set_id}/reject", response_model=GraphChangeSetRead)
def reject(change_set_id: str, db: Session = Depends(get_db)) -> GraphChangeSetRead:
    item = reject_change_set(db, get_change_set(db, change_set_id))
    return serialize_change_set(db, item)


@router.post("/{change_set_id}/apply", response_model=GraphChangeSetRead)
def apply(change_set_id: str, db: Session = Depends(get_db)) -> GraphChangeSetRead:
    item = apply_change_set(db, get_change_set(db, change_set_id))
    return serialize_change_set(db, item)


@router.post("/{change_set_id}/compensate", response_model=GraphChangeSetRead)
def compensate(change_set_id: str, db: Session = Depends(get_db)) -> GraphChangeSetRead:
    item = compensate_change_set(db, get_change_set(db, change_set_id))
    return serialize_change_set(db, item)
