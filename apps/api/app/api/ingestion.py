from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import LinkSubmission
from app.schemas.ingestion import LinkCreate, LinkReview
from app.services.ingestion import (
    approve_submission,
    create_submission,
    enqueue_submission,
    get_submission,
    serialize_submission,
)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/links", status_code=202)
def submit(data: LinkCreate, response: Response, db: Session = Depends(get_db)) -> dict:
    item, duplicate = create_submission(db, data)
    if duplicate:
        response.status_code = 200
    return serialize_submission(item)


@router.get("/links")
def links(status: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    statement = select(LinkSubmission).order_by(LinkSubmission.created_at.desc())
    if status:
        statement = statement.where(LinkSubmission.status == status)
    return [serialize_submission(item) for item in db.scalars(statement)]


@router.post("/links/{submission_id}/retry")
def retry(submission_id: str, provider: str | None = None, db: Session = Depends(get_db)) -> dict:
    item = get_submission(db, submission_id)
    return serialize_submission(enqueue_submission(db, item, provider))


@router.post("/links/{submission_id}/approve")
def approve(
    submission_id: str, data: LinkReview, db: Session = Depends(get_db)
) -> dict[str, str]:
    item = get_submission(db, submission_id)
    research = approve_submission(db, item, data)
    return {"status": item.status, "research_id": research.id}


@router.post("/links/{submission_id}/reject")
def reject(submission_id: str, db: Session = Depends(get_db)) -> dict:
    item = get_submission(db, submission_id)
    if item.status not in {"needs-review", "dead-letter"}:
        from fastapi import HTTPException

        raise HTTPException(409, f"Submission cannot be rejected in status {item.status}")
    item.status = "rejected"
    db.commit()
    return serialize_submission(item)
