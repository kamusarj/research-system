from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AuditEvent, KnowledgeGap
from app.schemas.gaps import GapAssign, GapDismiss, GapPrioritize, GapSnooze
from app.services.gaps import (
    approve_deep_research,
    detect_gaps,
    get_gap,
    request_deep_research,
    serialize_gap,
)
from app.services.research import serialize_research
from app.services.research_agent.runner import create_run

router = APIRouter(prefix="/gaps", tags=["knowledge-gaps"])
deep_research_router = APIRouter(prefix="/deep-research", tags=["knowledge-gaps"])


@router.get("")
def gaps(status: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    statement = select(KnowledgeGap).order_by(
        KnowledgeGap.priority.desc(), KnowledgeGap.updated_at.desc()
    )
    if status:
        statement = statement.where(KnowledgeGap.status == status)
    return [serialize_gap(gap) for gap in db.scalars(statement)]


@router.post("/detect")
def detect(max_coverage: int = Query(1, ge=1, le=20), db: Session = Depends(get_db)) -> list[dict]:
    return [serialize_gap(gap) for gap in detect_gaps(db, max_coverage)]


@router.post("/{gap_id}/prioritize")
def prioritize(gap_id: str, data: GapPrioritize, db: Session = Depends(get_db)) -> dict:
    gap = get_gap(db, gap_id)
    gap.priority = data.priority
    if gap.status == "detected":
        gap.status = "prioritized"
    db.commit()
    db.refresh(gap)
    return serialize_gap(gap)


@router.post("/{gap_id}/assign")
def assign(gap_id: str, data: GapAssign, db: Session = Depends(get_db)) -> dict:
    gap = get_gap(db, gap_id)
    gap.assigned_to = data.assigned_to
    gap.status = "assigned"
    db.add(
        AuditEvent(
            entity_type="knowledge-gap",
            entity_id=gap.id,
            action="gap.assigned",
            payload={"assigned_to": data.assigned_to},
        )
    )
    db.commit()
    db.refresh(gap)
    return serialize_gap(gap)


@router.post("/{gap_id}/dismiss")
def dismiss(gap_id: str, data: GapDismiss, db: Session = Depends(get_db)) -> dict:
    gap = get_gap(db, gap_id)
    gap.status = "dismissed"
    gap.metadata_json = {**(gap.metadata_json or {}), "dismissal_reason": data.reason}
    db.commit()
    db.refresh(gap)
    return serialize_gap(gap)


@router.post("/{gap_id}/snooze")
def snooze(gap_id: str, data: GapSnooze, db: Session = Depends(get_db)) -> dict:
    gap = get_gap(db, gap_id)
    until = data.until
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    if until <= datetime.now(UTC):
        from fastapi import HTTPException

        raise HTTPException(422, "Snooze time must be in the future")
    gap.snoozed_until = until
    gap.status = "snoozed"
    db.commit()
    db.refresh(gap)
    return serialize_gap(gap)


@router.post("/{gap_id}/request-deep-research", status_code=201)
def request(gap_id: str, db: Session = Depends(get_db)) -> dict:
    return serialize_research(request_deep_research(db, get_gap(db, gap_id))).model_dump()


@deep_research_router.post("/{research_id}/approve")
def approve(research_id: str, db: Session = Depends(get_db)) -> dict:
    return serialize_research(approve_deep_research(db, research_id)).model_dump()


@router.post("/{gap_id}/research-run", status_code=202)
def start_gap_research_run(gap_id: str, db: Session = Depends(get_db)) -> dict:
    """Chạy pipeline nghiên cứu sâu cho khoảng trống; báo cáo nháp sẽ gắn lại vào khoảng trống."""
    gap = get_gap(db, gap_id)
    if gap.status in {"dismissed", "filled"}:
        raise HTTPException(409, f"Cannot research a gap in status {gap.status}")
    question = f"{gap.title}: {gap.reason}"[:1000]
    run = create_run(db, question, knowledge_gap_id=gap.id)
    return {"id": run.id, "status": run.status, "stage": run.stage}

