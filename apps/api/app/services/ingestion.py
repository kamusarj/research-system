import hashlib
import logging
import ssl
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.identity import current_actor_id
from app.core.localization import product_error_message
from app.core.observability import exception_fields, observe_worker_job, provider_observation
from app.models import AuditEvent, LinkSubmission, ResearchItem, utcnow
from app.schemas.ingestion import LinkClassification, LinkCreate, LinkReview, TranscriptUpsert
from app.schemas.research import ResearchCreate
from app.schemas.source import NormalizedSource, SourceEvidence
from app.services.ai import PROVIDERS, provider
from app.services.chatgpt_plan import ChatGPTPlanError, ensure_owner_spends
from app.services.prompts import Source, injection_signals, task_prompt
from app.services.research import create_research, get_research_or_404, transition
from app.services.sources import adapter_for_url, normalize_url
from app.services.sources.article import ArticleSourceAdapter, parsed_title
from app.services.sources.browser import render_public_article
from app.services.sources.errors import SourceError
from app.services.sources.facebook import FacebookSourceAdapter, facebook_resource_kind

logger = logging.getLogger("research-worker.ingestion")

# Limitations a real browser can plausibly clear: the content exists, but a script or an
# interstitial stands between the plain fetch and it. A paywall is not on this list —
# rendering it would still return the preview, only more slowly.
BROWSER_RECOVERABLE_LIMITATIONS = {"JS_RENDER_REQUIRED", "CONSENT_WALL"}


@dataclass(slots=True)
class FetchedSourceResult:
    normalized: NormalizedSource

    def __iter__(self) -> Iterator[str]:
        yield self.normalized.canonical_url
        yield self.normalized.title
        yield self.normalized.raw_text


def fetch_url(
    url: str,
    on_stage: Callable[[str], None] | None = None,
) -> FetchedSourceResult:
    """Run normalize -> detect -> fetch -> extract for one URL."""

    normalized_url = normalize_url(url)
    adapter = adapter_for_url(normalized_url)
    if on_stage:
        on_stage("fetching")
    raw = adapter.fetch(normalized_url)
    resolved_adapter = adapter_for_url(raw.final_url, raw.content_type)
    if on_stage:
        on_stage("extracting")
    document = resolved_adapter.extract(raw)
    if (
        isinstance(resolved_adapter, ArticleSourceAdapter)
        and document.limitation_code in BROWSER_RECOVERABLE_LIMITATIONS
        and settings.browser_render_enabled
    ):
        rendered = render_public_article(document.canonical_url)
        if rendered.raw is not None:
            candidate = resolved_adapter.extract(rendered.raw)
            candidate.metadata = {
                **candidate.metadata,
                "browser_rendered": True,
                "browser_request_count": rendered.request_count,
                "browser_blocked_count": rendered.blocked_count,
            }
            if len(candidate.raw_text) > len(document.raw_text):
                document = candidate
        elif rendered.limitation_code:
            # Keep the limitation that describes the source. "The renderer is down" tells
            # a researcher nothing they can act on, while "this page needs JavaScript"
            # does; the renderer's own failure is recorded beside it for the operator.
            document.metadata = {
                **document.metadata,
                "browser_rendered": False,
                "browser_render_limitation": rendered.limitation_code,
                "browser_request_count": rendered.request_count,
                "browser_blocked_count": rendered.blocked_count,
            }
    return FetchedSourceResult(document)


def _format_timestamp(seconds: float) -> str:
    whole = int(seconds)
    hours, remainder = divmod(whole, 3600)
    minutes, second = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{second:02d}"


def _apply_source_overrides(document: NormalizedSource, item: LinkSubmission) -> NormalizedSource:
    transcript_data = (item.source_overrides or {}).get("transcript")
    if not transcript_data:
        return document
    transcript = TranscriptUpsert.model_validate(transcript_data)
    kind = document.metadata.get("resource_kind")
    if document.source_type != "facebook" or kind not in {"reel", "video"}:
        raise SourceError(
            "TRANSCRIPT_SOURCE_INVALID",
            "A transcript can only enrich a public Facebook Reel or video.",
        )
    lines = [
        f"[{_format_timestamp(segment.timestamp_seconds)}] {segment.text.strip()}"
        for segment in transcript.segments
    ]
    transcript_text = "\n".join(lines)
    document.raw_text = "\n\n".join(
        value
        for value in (document.description.strip(), "## Transcript\n" + transcript_text)
        if value
    )
    document.language = transcript.language
    document.evidence = [
        SourceEvidence(
            id=f"{document.id}:transcript:{index}",
            text=segment.text[:600],
            timestamp_seconds=segment.timestamp_seconds,
            location=f"timestamp:{_format_timestamp(segment.timestamp_seconds)}",
        )
        for index, segment in enumerate(transcript.segments[:100], start=1)
    ]
    override_metadata = (item.source_overrides or {}).get("transcript_metadata", {})
    document.metadata = {
        **document.metadata,
        "metadata_only": False,
        "transcript_source": "user_supplied",
        "transcript_language": transcript.language,
        "transcript_segment_count": len(transcript.segments),
        "transcript_supplied_by": override_metadata.get("supplied_by"),
        "transcript_supplied_at": override_metadata.get("supplied_at"),
    }
    document.collection_status = "EXTRACTED"
    document.limitation_code = None
    document.limitation_message = None
    return document


def serialize_submission(item: LinkSubmission) -> dict:
    transcript = (item.source_overrides or {}).get("transcript")
    transcript_metadata = (item.source_overrides or {}).get("transcript_metadata", {})
    classification = dict(item.classification or {})
    content_preview = item.extracted_markdown[:500]
    if transcript:
        normalized = dict(classification.get("normalized_source") or {})
        normalized["evidence"] = []
        classification["normalized_source"] = normalized
        classification["summary"] = normalized.get("description") or item.title or ""
        content_preview = normalized.get("description") or ""
    normalized = dict(classification.get("normalized_source") or {})
    limitation_code = normalized.get("limitation_code")
    if limitation_code:
        normalized["limitation_message"] = product_error_message(str(limitation_code), 400)
    elif normalized.get("limitation_message"):
        normalized["limitation_message"] = "Nguồn có một số giới hạn trích xuất cần được kiểm tra."
    if normalized:
        classification["normalized_source"] = normalized
    return {
        "id": item.id,
        "url": item.url,
        "source_type": item.source_type,
        "source_ref": item.source_ref,
        "submitted_by": item.submitted_by,
        "status": item.status,
        "stage": item.stage,
        "review_status": item.review_status,
        "title": item.title,
        "content_preview": content_preview,
        "classification": classification,
        "transcript": {
            "configured": bool(transcript),
            "language": transcript.get("language") if transcript else None,
            "segment_count": len(transcript.get("segments", [])) if transcript else 0,
            "updated_at": transcript_metadata.get("supplied_at"),
        },
        "provider_name": item.provider_name,
        "model_name": item.model_name,
        "attempt_count": item.attempt_count,
        "next_attempt_at": item.next_attempt_at,
        "error": product_error_message(item.error_code, 400) if item.error_code else None,
        "error_code": item.error_code,
        "error_details": item.error_details or {},
        "research_id": item.research_id,
        "duplicate_of_id": item.duplicate_of_id,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def get_submission(db: Session, submission_id: str) -> LinkSubmission:
    item = db.get(LinkSubmission, submission_id)
    if not item:
        raise HTTPException(404, "Link submission not found")
    return item


def _set_stage(db: Session, item: LinkSubmission, stage: str) -> None:
    item.stage = stage
    item.status = stage if stage in {"fetching", "extracting", "analyzing"} else "processing"
    item.next_attempt_at = utcnow() + timedelta(seconds=settings.intake_job_lease_seconds)
    db.commit()


def _classification_payload(document: NormalizedSource) -> dict:
    return {
        "content_type": document.source_type,
        "language": document.language,
        "summary": document.summary or document.description,
        "concepts": [],
        "technologies": [],
        "agent_patterns": [],
        "business_domains": [],
        "tags": [],
        "relations": [],
        "relevance_score": 0,
        "confidence": 0,
        "reasoning": document.limitation_message or "Đang chờ con người kiểm duyệt",
        "normalized_source": document.model_dump(mode="json", exclude={"raw_text"}),
    }


def auto_approval_allowed(item: LinkSubmission, final_url: str) -> bool:
    """Tự duyệt dựa trên tín hiệu phía máy chủ, không chỉ điểm tin cậy do mô hình tự báo:
    nội dung đọc được đầy đủ, không có dấu hiệu điều khiển mô hình, tên miền nằm trong danh
    sách cho phép (nếu cấu hình)."""
    classification = item.classification or {}
    if not item.auto_approve or item.status != "completed":
        return False
    if classification.get("untrusted_signals"):
        return False
    allowed_domains = settings.auto_approve_domains
    if allowed_domains:
        host = (urlsplit(final_url).hostname or "").lower()
        if not any(host == domain or host.endswith(f".{domain}") for domain in allowed_domains):
            return False
    confidence = float(classification.get("confidence", 0))
    return confidence >= settings.intake_auto_approve_confidence


def process_submission(db: Session, item: LinkSubmission) -> LinkSubmission:
    job_id = item.id
    try:
        fetched = fetch_url(item.url, lambda stage: _set_stage(db, item, stage))
        final_url, title, content = fetched
        document = fetched.normalized
        document = _apply_source_overrides(document, item)
        final_url, title, content = document.canonical_url, document.title, document.raw_text
        content_for_hash = content or f"{final_url}\n{title}\n{document.description}"
        if not content_for_hash.strip():
            raise SourceError("EMPTY_CONTENT", "The source contains no usable content or metadata")
        digest = hashlib.sha256(content_for_hash.encode()).hexdigest()
        duplicate = db.scalar(
            select(LinkSubmission)
            .where(
                LinkSubmission.id != item.id,
                or_(LinkSubmission.url == final_url, LinkSubmission.content_hash == digest),
                LinkSubmission.status != "failed",
                # A rejected source must not block collecting it again. Rejection is a
                # judgement about one record, not a permanent ban on the material.
                LinkSubmission.review_status != "rejected",
            )
            # Prefer an original that is already published: inheriting its research record
            # is what makes the duplicate useful rather than a dead end.
            .order_by(LinkSubmission.research_id.is_(None), LinkSubmission.created_at)
        )
        # The canonical URL is unique across submissions. When a redirect lands on a page
        # another row already owns, adopting it would violate that index and turn an
        # ordinary duplicate into a database error the worker retries to exhaustion.
        # Keeping the submitted address also records which link a person actually sent.
        if duplicate is None or duplicate.url != final_url:
            item.url = final_url
        item.title = title[:500]
        item.extracted_markdown = content
        item.content_hash = digest
        item.classification = _classification_payload(document)
        if duplicate:
            item.status = "completed"
            item.stage = "completed"
            item.review_status = "duplicate"
            item.duplicate_of_id = duplicate.id
            item.research_id = duplicate.research_id
            item.next_attempt_at = None
            item.finished_at = utcnow()
            db.commit()
            logger.info(
                "Intake job completed as duplicate",
                extra={
                    "action": "worker.job.duplicate",
                    "job_id": job_id,
                    "outcome": "published" if duplicate.research_id else "awaiting_original",
                },
            )
            return item

        if len(content.strip()) >= 80:
            _set_stage(db, item, "analyzing")
            # Gói ChatGPT riêng tính vào người đã gửi link, kể cả khi người khác bấm thử lại.
            runtime = provider(item.provider_name, user_id=item.submitted_by)
            prompt = task_prompt(
                "Classify this source for an AI-agents-for-business research knowledge base. "
                "Return grounded structured JSON only. Do not invent technologies or relations.",
                sources=[
                    Source(
                        content,
                        attributes={
                            "type": document.source_type,
                            "url": final_url,
                            "title": title,
                        },
                    )
                ],
                max_chars_per_source=30000,
            )
            with provider_observation(
                provider=item.provider_name or settings.ai_provider,
                model=runtime.name,
                operation="link-classification",
            ):
                classification = runtime.complete_json(prompt, LinkClassification)
            item.classification = classification.model_dump()
            item.classification["normalized_source"] = document.model_dump(
                mode="json", exclude={"raw_text"}
            )
            signals = injection_signals(content[:30000])
            if signals:
                # Người duyệt thấy cảnh báo; tự duyệt bị chặn bên dưới.
                item.classification["untrusted_signals"] = signals
            item.provider_name = item.provider_name or settings.ai_provider
            item.model_name = runtime.name

        item.status = "partial_success" if document.collection_status == "PARTIAL" else "completed"
        item.stage = "completed"
        item.review_status = "needs_review"
        item.next_attempt_at = None
        item.finished_at = utcnow()
        item.error = None
        item.error_code = None
        item.error_details = {}
        db.commit()
        logger.info(
            "Intake job completed",
            extra={"job_id": job_id, "status": item.status, "source_type": document.source_type},
        )
        if auto_approval_allowed(item, final_url):
            approve_submission(db, item, LinkReview())
    except Exception as exc:
        db.rollback()
        item = db.get(LinkSubmission, item.id)
        if item:
            error = _source_error(exc, item.stage)
            if error.user_actionable:
                logger.info(
                    "Intake job stopped on an actionable source limitation",
                    extra={
                        "action": "worker.job.actionable",
                        "job_id": job_id,
                        "stage": item.stage,
                        "error_code": error.code,
                    },
                )
            else:
                # Exception messages may carry credentials or document content, so only the
                # type and code location are logged alongside the mapped error code.
                logger.warning(
                    "Intake job did not complete",
                    extra={
                        "action": "worker.job.failed",
                        "job_id": job_id,
                        "stage": item.stage,
                        "error_code": error.code,
                        **exception_fields(exc),
                    },
                )
            item.error = error.message[:2000]
            item.error_code = error.code
            item.error_details = error.details
            if error.retryable and item.attempt_count < settings.intake_max_attempts:
                item.status = "pending"
                item.stage = "retry_scheduled"
                delay = settings.intake_retry_base_seconds * (2 ** (item.attempt_count - 1))
                item.next_attempt_at = utcnow() + timedelta(seconds=delay)
            else:
                item.status = "failed"
                item.stage = "failed"
                item.review_status = "not_requested"
                item.next_attempt_at = None
                item.finished_at = utcnow()
            db.commit()
        else:
            logger.exception("Intake job disappeared after failure", extra={"job_id": job_id})
    return item


def _source_error(exc: Exception, stage: str | None = None) -> SourceError:
    if isinstance(exc, SourceError):
        return exc
    if isinstance(exc, ChatGPTPlanError):
        return SourceError(
            exc.code,  # type: ignore[arg-type]
            exc.message,
            retryable=exc.retryable,
            status_code=exc.status_code,
        )
    if stage == "analyzing":
        if isinstance(exc, httpx.HTTPStatusError):
            status_code = exc.response.status_code
            if status_code in {401, 403}:
                return SourceError(
                    "AI_PROVIDER_AUTH_FAILED",
                    "The AI provider rejected its configured credentials",
                    status_code=status_code,
                )
            if status_code == 429:
                return SourceError(
                    "AI_PROVIDER_RATE_LIMITED",
                    "The AI provider rate limit was reached",
                    retryable=True,
                    status_code=status_code,
                )
            return SourceError(
                "AI_PROVIDER_UNAVAILABLE" if status_code >= 500 else "AI_PROVIDER_ERROR",
                "The AI provider could not complete classification",
                retryable=status_code >= 500,
                status_code=status_code,
            )
        if isinstance(exc, httpx.RequestError):
            return SourceError(
                "AI_PROVIDER_UNAVAILABLE",
                "The AI provider could not be reached",
                retryable=True,
            )
        if isinstance(exc, ValidationError | KeyError):
            return SourceError(
                "AI_RESPONSE_INVALID",
                "The AI provider returned an invalid structured response",
            )
    if isinstance(exc, httpx.TimeoutException):
        return SourceError("FETCH_TIMEOUT", "The source request timed out", retryable=True)
    if isinstance(exc, httpx.ConnectError):
        return SourceError("DNS_FAILED", "The source host could not be reached", retryable=True)
    if isinstance(exc, ssl.SSLError):
        return SourceError("TLS_FAILED", "The source has an untrusted or invalid certificate")
    if isinstance(exc, httpx.RequestError | OSError):
        return SourceError("FETCH_FAILED", "The source could not be reached", retryable=True)
    if isinstance(exc, SQLAlchemyError):
        return SourceError(
            "DATABASE_ERROR",
            "The database rejected this update; it will be retried",
            retryable=True,
        )
    if isinstance(exc, UnicodeError):
        return SourceError("EXTRACTION_FAILED", "The source text could not be decoded")
    if isinstance(exc, ValueError):
        return SourceError("EXTRACTION_FAILED", "Source extraction failed")
    # The exception type is repository-owned and safe to persist; its message is not.
    return SourceError(
        "INTERNAL_ERROR",
        "The source could not be processed",
        details={"exception_type": type(exc).__qualname__, "stage": stage or "unknown"},
    )


def is_retryable(exc: Exception) -> bool:
    return _source_error(exc).retryable


def claim_next_submission(db: Session) -> LinkSubmission | None:
    now = utcnow()
    ready = and_(
        LinkSubmission.status == "pending",
        or_(LinkSubmission.next_attempt_at.is_(None), LinkSubmission.next_attempt_at <= now),
    )
    expired_lease = and_(
        LinkSubmission.status.in_({"processing", "fetching", "extracting", "analyzing"}),
        LinkSubmission.next_attempt_at.is_not(None),
        LinkSubmission.next_attempt_at <= now,
    )
    # Lease hết hạn nghĩa là worker bị dừng giữa chừng (khởi động lại, hết bộ nhớ). Không nhận lại
    # vô hạn: tác vụ đã dùng hết lượt thử được kết thúc để không lặp lại sự cố mãi mãi.
    db.execute(
        update(LinkSubmission)
        .where(expired_lease, LinkSubmission.attempt_count >= settings.intake_max_attempts)
        .values(
            status="failed",
            stage="failed",
            review_status="not_requested",
            error_code="WORKER_LEASE_EXPIRED",
            error="The worker stopped before this job finished",
            next_attempt_at=None,
            finished_at=now,
        )
        .execution_options(synchronize_session=False)
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
        db.commit()
        return None
    item.status = "processing"
    item.stage = "normalizing"
    item.attempt_count += 1
    item.error = None
    item.error_code = None
    item.error_details = {}
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
        started = time.monotonic()
        result = process_submission(db, item)
        outcome = (
            "success"
            if result.status in {"completed", "partial_success"}
            else "retry"
            if result.status == "pending"
            else "error"
        )
        duration_seconds = time.monotonic() - started
        observe_worker_job(
            job_type="link-intake",
            outcome=outcome,
            error_code=result.error_code,
            duration_seconds=duration_seconds,
        )
        logger.info(
            "Worker job completed",
            extra={
                "action": "worker.job.completed",
                "job_id": result.id,
                "job_type": "link-intake",
                "stage": result.stage,
                "outcome": outcome,
                "error_code": result.error_code,
                "duration_ms": round(duration_seconds * 1000, 2),
            },
        )
        processed += 1
    return processed


def enqueue_submission(
    db: Session, item: LinkSubmission, provider_name: str | None = None
) -> LinkSubmission:
    if item.status != "failed":
        raise HTTPException(409, f"Submission cannot be retried in status {item.status}")
    ensure_owner_spends(provider_name or item.provider_name, item.submitted_by)
    item.status = "pending"
    item.stage = "pending"
    item.review_status = "not_requested"
    item.attempt_count = 0
    item.next_attempt_at = utcnow()
    item.started_at = None
    item.finished_at = None
    item.error = None
    item.error_code = None
    item.error_details = {}
    if provider_name:
        item.provider_name = provider_name
    elif item.provider_name not in PROVIDERS:
        item.provider_name = settings.ai_provider
    db.commit()
    db.refresh(item)
    return item


def upsert_transcript(
    db: Session, item: LinkSubmission, transcript: TranscriptUpsert
) -> LinkSubmission:
    facebook = FacebookSourceAdapter()
    if not facebook.can_handle(item.url) or facebook_resource_kind(item.url) not in {
        "reel",
        "video",
    }:
        raise HTTPException(422, "A transcript can only be attached to a Facebook Reel or video")
    if item.review_status == "approved" or item.research_id is not None:
        raise HTTPException(409, "An approved or published submission cannot be changed")

    now = utcnow()
    supplied_by = current_actor_id()
    item.source_overrides = {
        **(item.source_overrides or {}),
        "transcript": transcript.model_dump(mode="json"),
        "transcript_metadata": {
            "supplied_by": supplied_by,
            "supplied_at": now.isoformat(),
        },
    }
    item.status = "pending"
    item.stage = "pending"
    item.review_status = "not_requested"
    item.attempt_count = 0
    item.next_attempt_at = now
    item.started_at = None
    item.finished_at = None
    item.extracted_markdown = ""
    item.content_hash = None
    item.classification = {}
    item.model_name = None
    item.error = None
    item.error_code = None
    item.error_details = {}
    db.add(
        AuditEvent(
            entity_type="link_submission",
            entity_id=item.id,
            action="link.transcript.upserted",
            actor=supplied_by,
            payload={
                "language": transcript.language,
                "segment_count": len(transcript.segments),
            },
        )
    )
    db.commit()
    db.refresh(item)
    return item


def create_submission(db: Session, data: LinkCreate):
    from app.services.intake_receipts import create_compatibility_submission

    return create_compatibility_submission(db, data)


def review_backlog(db: Session) -> dict:
    """Summarise what is waiting on a human, so the queue is not something to discover.

    Sources that finished extraction but were never reviewed contribute nothing to the
    knowledge graph, and nothing in the product previously said how many there were.
    """

    counts = dict(
        db.execute(
            select(LinkSubmission.review_status, func.count()).group_by(
                LinkSubmission.review_status
            )
        ).all()
    )
    failed = db.scalar(
        select(func.count()).select_from(LinkSubmission).where(LinkSubmission.status == "failed")
    )
    stranded = db.scalar(
        select(func.count())
        .select_from(LinkSubmission)
        .where(
            LinkSubmission.review_status == "duplicate",
            LinkSubmission.research_id.is_(None),
        )
    )
    return {
        "needs_review": int(counts.get("needs_review", 0)),
        "approved": int(counts.get("approved", 0)),
        "rejected": int(counts.get("rejected", 0)),
        "duplicate": int(counts.get("duplicate", 0)),
        "not_requested": int(counts.get("not_requested", 0)),
        "failed": int(failed or 0),
        # Duplicates of an original nobody has published yet: they will inherit a research
        # record the moment that original is approved.
        "duplicates_awaiting_original": int(stranded or 0),
        "auto_approve_confidence": settings.intake_auto_approve_confidence,
    }


def reviewable_submissions(db: Session, limit: int = 200) -> list[LinkSubmission]:
    return list(
        db.scalars(
            select(LinkSubmission)
            .where(LinkSubmission.review_status == "needs_review")
            .order_by(LinkSubmission.created_at)
            .limit(limit)
        )
    )


def approve_submission(db: Session, item: LinkSubmission, review: LinkReview) -> ResearchItem:
    # Khóa bản ghi và làm mới trạng thái: hai lượt duyệt song song (bấm đúp, duyệt hàng loạt cùng
    # lúc với duyệt lẻ, worker tự duyệt) không được cùng xuất bản một nguồn.
    locked = db.scalar(
        select(LinkSubmission)
        .where(LinkSubmission.id == item.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if locked is not None:
        item = locked
    if item.review_status != "needs_review":
        raise HTTPException(
            409, f"Submission cannot be approved in review status {item.review_status}"
        )
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
            authors=normalized_source.get("authors", []),
            tags=tags,
            metadata=metadata,
        ),
        commit=False,
    )
    # Toàn bộ lượt duyệt là một giao dịch: nếu bước đề xuất đồ thị hoặc quét khoảng trống lỗi,
    # nghiên cứu chưa được xuất bản và có thể duyệt lại mà không tạo bản trùng.
    transition(db, research, "submit-review", commit=False)
    transition(db, research, "approve", commit=False)
    item.review_status = "approved"
    item.research_id = research.id

    # Submissions that arrived while this one was unpublished were parked with no research
    # record. Publishing the original is the moment they become useful, so they inherit it.
    waiting = db.scalars(
        select(LinkSubmission).where(
            LinkSubmission.duplicate_of_id == item.id,
            LinkSubmission.research_id.is_(None),
        )
    )
    for follower in waiting:
        follower.research_id = research.id

    # Publishing a source is only half the job: without this the knowledge it carries
    # never reaches the canonical hierarchy. The proposal stays a draft for human review.
    from app.services.link_mapping import create_link_change_set

    change_set = create_link_change_set(db, item, research.id)
    logger.info(
        "Link submission approved",
        extra={
            "action": "link.submission.approved",
            "job_id": item.id,
            "outcome": "proposed" if change_set else "no_placements",
        },
    )
    # Approval changes graph coverage. Refresh the canonical gap lifecycle in the same
    # unit of work so receipt clients (including Discord) can immediately report only the
    # gaps related to this newly approved research item.
    from app.services.gaps import detect_gaps

    detect_gaps(db, commit=False)
    db.commit()
    return get_research_or_404(db, research.id)
