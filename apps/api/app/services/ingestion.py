import hashlib
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta

import httpx
from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import LinkSubmission, ResearchItem, utcnow
from app.schemas.ingestion import LinkClassification, LinkCreate, LinkReview
from app.schemas.research import ResearchCreate
from app.schemas.source import NormalizedSource
from app.services.ai import provider
from app.services.research import create_research, transition
from app.services.sources import adapter_for_url, normalize_url
from app.services.sources.article import parsed_title


@dataclass
class FetchedSourceResult:
    normalized: NormalizedSource

    def __iter__(self) -> Iterator[str]:
        yield self.normalized.canonical_url
        yield self.normalized.title
        yield self.normalized.raw_text


def fetch_url(url: str) -> FetchedSourceResult:
    """Compatibility wrapper around the source adapter registry used by the worker."""
    return FetchedSourceResult(adapter_for_url(url).collect(url))


def serialize_submission(item: LinkSubmission) -> dict:
    return {
        "id": item.id,
        "url": item.url,
        "source_type": item.source_type,
        "source_ref": item.source_ref,
        "submitted_by": item.submitted_by,
        "status": item.status,
        "title": item.title,
        "content_preview": item.extracted_markdown[:500],
        "classification": item.classification or {},
        "provider_name": item.provider_name,
        "model_name": item.model_name,
        "attempt_count": item.attempt_count,
        "next_attempt_at": item.next_attempt_at,
        "error": item.error,
        "research_id": item.research_id,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def get_submission(db: Session, submission_id: str) -> LinkSubmission:
    item = db.get(LinkSubmission, submission_id)
    if not item:
        raise HTTPException(404, "Link submission not found")
    return item


def process_submission(db: Session, item: LinkSubmission) -> LinkSubmission:
    try:
        fetched = fetch_url(item.url)
        final_url, title, content = fetched
        normalized = getattr(fetched, "normalized", None)
        if normalized and normalized.collection_status != "EXTRACTED":
            item.url = final_url
            item.title = title[:500]
            item.extracted_markdown = content
            item.content_hash = hashlib.sha256(final_url.encode()).hexdigest()
            item.classification = {
                "content_type": normalized.source_type,
                "summary": normalized.summary,
                "normalized_source": normalized.model_dump(mode="json", exclude={"raw_text"}),
            }
            item.status = (
                "needs-transcript"
                if normalized.collection_status == "NEEDS_TRANSCRIPT"
                else "needs-text-layer"
            )
            item.next_attempt_at = None
            item.finished_at = utcnow()
            db.commit()
            return item
        if len(content) < 80:
            raise ValueError("Extracted content is too short to classify")
        digest = hashlib.sha256(content.encode()).hexdigest()
        duplicate = db.scalar(
            select(LinkSubmission).where(
                LinkSubmission.id != item.id,
                or_(LinkSubmission.url == final_url, LinkSubmission.content_hash == digest),
                LinkSubmission.status.notin_({"failed", "dead-letter"}),
            )
        )
        item.url = final_url
        item.title = title[:500]
        item.extracted_markdown = content
        item.content_hash = digest
        if duplicate:
            item.status = "duplicate"
            item.research_id = duplicate.research_id
            item.next_attempt_at = None
            item.finished_at = utcnow()
            db.commit()
            return item
        runtime = provider(item.provider_name)
        prompt = (
            "Classify this web content for an AI-agents-for-business research knowledge base. "
            "Return grounded structured JSON only. Do not invent technologies or relations.\n"
            f"URL: {final_url}\nTitle: {title}\nContent: {content[:30000]}"
        )
        classification = runtime.complete_json(prompt, LinkClassification)
        item.classification = classification.model_dump()
        if normalized:
            item.classification["normalized_source"] = normalized.model_dump(
                mode="json", exclude={"raw_text"}
            )
        item.provider_name = item.provider_name or settings.ai_provider
        item.model_name = runtime.name
        item.status = "needs-review"
        item.next_attempt_at = None
        item.finished_at = utcnow()
        db.commit()
        if (
            item.auto_approve
            and classification.confidence >= settings.intake_auto_approve_confidence
        ):
            approve_submission(db, item, LinkReview())
    except Exception as exc:
        db.rollback()
        item = db.get(LinkSubmission, item.id)
        if item:
            item.error = str(exc)[:2000]
            if is_retryable(exc) and item.attempt_count < settings.intake_max_attempts:
                item.status = "retrying"
                delay = settings.intake_retry_base_seconds * (2 ** (item.attempt_count - 1))
                item.next_attempt_at = utcnow() + timedelta(seconds=delay)
            else:
                item.status = "dead-letter"
                item.next_attempt_at = None
                item.finished_at = utcnow()
            db.commit()
    return item


def is_retryable(exc: Exception) -> bool:
    if isinstance(exc, HTTPException):
        return False
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status in {408, 425, 429} or status >= 500
    if isinstance(exc, httpx.RequestError):
        return True
    return not isinstance(exc, ValueError)


def claim_next_submission(db: Session) -> LinkSubmission | None:
    now = utcnow()
    ready = and_(
        LinkSubmission.status.in_({"queued", "retrying"}),
        or_(LinkSubmission.next_attempt_at.is_(None), LinkSubmission.next_attempt_at <= now),
    )
    expired_lease = and_(
        LinkSubmission.status == "extracting",
        LinkSubmission.next_attempt_at.is_not(None),
        LinkSubmission.next_attempt_at <= now,
    )
    statement = (
        select(LinkSubmission)
        .where(or_(ready, expired_lease))
        .order_by(LinkSubmission.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    item = db.scalar(statement)
    if not item:
        return None
    item.status = "extracting"
    item.attempt_count += 1
    item.error = None
    item.started_at = now
    item.finished_at = None
    item.next_attempt_at = now + timedelta(seconds=settings.intake_job_lease_seconds)
    db.commit()
    db.refresh(item)
    return item


def run_pending_submissions(db: Session, max_jobs: int = 10) -> int:
    processed = 0
    while processed < max_jobs:
        item = claim_next_submission(db)
        if not item:
            break
        process_submission(db, item)
        processed += 1
    return processed


def enqueue_submission(
    db: Session, item: LinkSubmission, provider_name: str | None = None
) -> LinkSubmission:
    if item.status not in {"dead-letter", "failed"}:
        raise HTTPException(409, f"Submission cannot be retried in status {item.status}")
    item.status = "queued"
    item.attempt_count = 0
    item.next_attempt_at = utcnow()
    item.started_at = None
    item.finished_at = None
    item.error = None
    if provider_name:
        item.provider_name = provider_name
    db.commit()
    db.refresh(item)
    return item


def create_submission(db: Session, data: LinkCreate) -> tuple[LinkSubmission, bool]:
    url = normalize_url(str(data.url))
    existing = db.scalar(select(LinkSubmission).where(LinkSubmission.url == url))
    if existing:
        if existing.status in {"dead-letter", "failed"}:
            existing.auto_approve = data.auto_approve
            return enqueue_submission(db, existing, data.provider), False
        return existing, True
    item = LinkSubmission(
        url=url,
        source_type=data.source_type,
        source_ref=data.source_ref,
        submitted_by=data.submitted_by,
        provider_name=data.provider or settings.ai_provider,
        auto_approve=data.auto_approve,
        next_attempt_at=utcnow(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item, False


def approve_submission(db: Session, item: LinkSubmission, review: LinkReview) -> ResearchItem:
    if item.status not in {"needs-review", "classified"}:
        raise HTTPException(409, f"Submission cannot be approved in status {item.status}")
    values = item.classification or {}
    tags = review.tags if review.tags is not None else values.get("tags", [])
    normalized_source = values.get("normalized_source", {})
    metadata = {
        "link_submission_id": item.id,
        "source_type": normalized_source.get("source_type", item.source_type),
        "submission_source_type": item.source_type,
        "source_ref": item.source_ref,
        "classification": values,
        "ai_provider": item.provider_name,
        "ai_model": item.model_name,
    }
    research = create_research(
        db,
        ResearchCreate(
            title=review.title or item.title or parsed_title(item.url),
            type="reference",
            collection_method="auto-collected",
            summary=review.summary or values.get("summary"),
            content=item.extracted_markdown,
            source_url=item.url,
            external_id=item.content_hash,
            tags=tags,
            metadata=metadata,
        ),
    )
    transition(db, research, "submit-review")
    transition(db, research, "approve")
    item.status = "approved"
    item.research_id = research.id
    db.commit()
    return research
