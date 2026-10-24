import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.observability import exception_fields
from app.db import get_db
from app.models import LinkSubmission
from app.schemas.ingestion import (
    AIProviderName,
    BulkLinkReview,
    BulkLinkReviewResult,
    LinkCreate,
    LinkReview,
    LinkSubmissionStatus,
    ReviewBacklog,
    TranscriptUpsert,
)
from app.services.ingestion import (
    approve_submission,
    create_submission,
    enqueue_submission,
    get_submission,
    review_backlog,
    reviewable_submissions,
    serialize_submission,
    upsert_transcript,
)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])
logger = logging.getLogger("research-api.ingestion")


@router.post("/links", status_code=202)
def submit(data: LinkCreate, response: Response, db: Session = Depends(get_db)) -> dict:
    item, duplicate, delivery = create_submission(db, data)
    if duplicate:
        response.status_code = 200
    payload = serialize_submission(item)
    receipt_item_id, receipt_disposition = next(iter(delivery.dispositions.items()))
    payload.update(
        {
            "receipt_id": delivery.receipt.id,
            "receipt_item_id": receipt_item_id,
            "receipt_disposition": receipt_disposition,
            "receipt_replayed": delivery.replayed,
        }
    )
    return payload


@router.get("/links")
def links(
    status: LinkSubmissionStatus | None = None,
    # Giao diện thăm dò danh sách này mỗi 1,5 giây khi có tác vụ chạy; mỗi dòng mang cả nội dung
    # trích xuất (tới 2 MB) nên chỉ trả các liên kết gần nhất.
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[dict]:
    statement = select(LinkSubmission).order_by(LinkSubmission.created_at.desc()).limit(limit)
    if status:
        statement = statement.where(LinkSubmission.status == status)
    return [serialize_submission(item) for item in db.scalars(statement)]


@router.get("/links/backlog", response_model=ReviewBacklog)
def backlog(db: Session = Depends(get_db)) -> ReviewBacklog:
    return ReviewBacklog.model_validate(review_backlog(db))


@router.post("/links/bulk-review")
def bulk_review(data: BulkLinkReview, db: Session = Depends(get_db)) -> BulkLinkReviewResult:
    """Decide many queued submissions at once, reporting each outcome separately.

    One submission failing its own state check must not silently discard the rest of the
    reviewer's decisions, so every item is attempted and its result is returned.
    """

    targets = (
        [get_submission(db, submission_id) for submission_id in data.submission_ids]
        if data.submission_ids
        else reviewable_submissions(db)
    )
    approved: list[str] = []
    rejected: list[str] = []
    skipped: list[dict[str, str]] = []
    for item in targets:
        if item.review_status != "needs_review":
            skipped.append({"id": item.id, "reason": f"review status is {item.review_status}"})
            continue
        try:
            if data.decision == "approve":
                approve_submission(db, item, LinkReview())
                approved.append(item.id)
            else:
                item.review_status = "rejected"
                db.commit()
                rejected.append(item.id)
        except HTTPException as failure:
            db.rollback()
            skipped.append({"id": item.id, "reason": str(failure.detail)})
        except Exception as failure:
            # The contract of this endpoint is that one bad item never discards the rest of
            # the reviewer's decisions, so an unexpected failure is reported per item too.
            # The exception type is repository-owned and safe; its message is not.
            db.rollback()
            logger.warning(
                "Bulk review could not decide one submission",
                extra={
                    "action": "intake.bulk_review.item_failed",
                    "job_id": item.id,
                    **exception_fields(failure),
                },
            )
            skipped.append({"id": item.id, "reason": type(failure).__qualname__})
    return BulkLinkReviewResult(
        approved=approved,
        rejected=rejected,
        skipped=skipped,
        backlog=ReviewBacklog.model_validate(review_backlog(db)),
    )


@router.post("/links/{submission_id}/retry")
def retry(
    submission_id: str,
    provider: AIProviderName | None = None,
    db: Session = Depends(get_db),
) -> dict:
    item = get_submission(db, submission_id)
    return serialize_submission(enqueue_submission(db, item, provider))


@router.put("/links/{submission_id}/transcript")
def transcript(
    submission_id: str,
    data: TranscriptUpsert,
    db: Session = Depends(get_db),
) -> dict:
    item = get_submission(db, submission_id)
    return serialize_submission(upsert_transcript(db, item, data))


@router.post("/links/{submission_id}/approve")
def approve(submission_id: str, data: LinkReview, db: Session = Depends(get_db)) -> dict[str, str]:
    item = get_submission(db, submission_id)
    research = approve_submission(db, item, data)
    return {"status": item.status, "research_id": research.id}


@router.post("/links/{submission_id}/reject")
def reject(submission_id: str, db: Session = Depends(get_db)) -> dict:
    item = get_submission(db, submission_id)
    if item.review_status != "needs_review":
        raise HTTPException(
            409, f"Submission cannot be rejected in review status {item.review_status}"
        )
    item.review_status = "rejected"
    db.commit()
    return serialize_submission(item)
