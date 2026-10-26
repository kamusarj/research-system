import asyncio
import hashlib
import logging
import time
from datetime import timedelta

import httpx
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.observability import exception_fields, observe_worker_job, provider_observation
from app.models import (
    AIOutput,
    Attachment,
    AuditEvent,
    DocumentGraphEdge,
    DocumentGraphNode,
    DocumentGraphWorkspace,
    KnowledgeNode,
    PaperEvaluation,
    ResearchItem,
    utcnow,
)
from app.schemas.documents import DocumentGraphExtraction
from app.schemas.paper_fit import (
    PaperFitAssessment,
    PaperFitDimensions,
    PaperFitHardGates,
    PaperFitProviderAssessment,
)
from app.services.ai import PROVIDERS, provider
from app.services.chatgpt_plan import ensure_owner_spends
from app.services.document_graph import (
    ExtractedDocument,
    clear_document_graph,
    document_graph_prompt,
    extract_document,
    replace_document_graph,
)
from app.services.document_rag import refresh_document_rag
from app.services.documents import get_object_storage
from app.services.object_storage import DocumentError, ObjectStorage
from app.services.paper_duplicates import find_near_duplicate_workspaces
from app.services.paper_fit import evaluate_paper_fit
from app.services.placement import resolve_matched_pillars
from app.services.prompts import Source, task_prompt

logger = logging.getLogger("research-worker.documents")
PAPER_FIT_PROMPT_VERSION = "business-ai-agents-paper-fit-prompt-v1"
DOCUMENT_GRAPH_PROMPT_VERSION = "business-ai-agents-document-graph-prompt-v2"
SUPPORTED_LANGUAGES = {"en", "english", "vi", "vietnamese", "vietnamese language"}


class DocumentProcessingError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


def paper_fit_prompt(title: str, extracted: ExtractedDocument, pillars: list[str]) -> str:
    return task_prompt(
        "Evaluate this source for the Business AI Agents research system. Return only the semantic "
        "dimension inputs requested by the JSON schema. The server calculates hard gates, weighted "
        "score, and routing; do not invent a final score. Ground the reasoning in the supplied "
        "text. Use only matching canonical pillar labels from <context> when possible. Dimension "
        "scores are 0-100.",
        sources=[Source(extracted.text, attributes={"title": title})],
        max_chars_per_source=40000,
        trusted_context=f"Canonical pillars: {pillars}",
    )


def _set_stage(db: Session, workspace: DocumentGraphWorkspace, stage: str) -> None:
    workspace.processing_status = stage
    workspace.next_attempt_at = utcnow() + timedelta(seconds=settings.document_worker_lease_seconds)
    db.commit()


def _zero_dimensions() -> PaperFitDimensions:
    return PaperFitDimensions(
        system_fit=0,
        business_applicability=0,
        evidence_quality=0,
        novelty=0,
        implementation_value=0,
        gap_coverage=0,
        freshness=0,
    )


def _provider_assessment(
    db: Session,
    workspace: DocumentGraphWorkspace,
    research: ResearchItem,
    extracted: ExtractedDocument,
):
    runtime = provider(workspace.provider_name, user_id=workspace.requested_by)
    pillars = list(
        db.scalars(
            select(KnowledgeNode.canonical_label)
            .where(
                KnowledgeNode.node_type == "SystemPillar",
                KnowledgeNode.lifecycle_status == "approved",
            )
            .order_by(KnowledgeNode.canonical_label)
        )
    )
    prompt = paper_fit_prompt(research.title, extracted, pillars)
    with provider_observation(
        provider=workspace.provider_name or settings.ai_provider,
        model=runtime.name,
        operation="paper-fit",
    ):
        proposal = runtime.complete_json(prompt, PaperFitProviderAssessment)
    language = proposal.detected_language.casefold().strip()
    language_base = language.replace("_", "-").split("-", 1)[0]
    assessment = PaperFitAssessment(
        hard_gates=PaperFitHardGates(
            supported_access=True,
            readable_content=bool(extracted.text.strip()),
            not_duplicate=True,
            has_title=bool(research.title.strip()),
            has_provenance=bool(workspace.content_hash and workspace.attachment_id),
            supported_language=(
                language in SUPPORTED_LANGUAGES or language_base in SUPPORTED_LANGUAGES
            ),
            safe_file=True,
            content_valid=bool(extracted.text.strip()),
        ),
        dimensions=proposal.dimensions,
        matched_pillars=resolve_matched_pillars(
            research.title, extracted.text, proposal.matched_pillars, pillars
        ),
        candidate_parents=proposal.candidate_parents,
        contribution_types=proposal.contribution_types,
        overlaps_with=proposal.overlaps_with,
        fills_gaps=proposal.fills_gaps,
        limitations=proposal.limitations,
        reasoning_summary=proposal.reasoning_summary,
        confidence=proposal.confidence,
    )
    result = evaluate_paper_fit(assessment)
    duplicates = find_near_duplicate_workspaces(db, workspace.id, research.title, result.dimensions)
    if duplicates:
        result.overlaps_with = list(
            dict.fromkeys([*result.overlaps_with, *(item[0] for item in duplicates)])
        )
        result.limitations = [
            *result.limitations,
            f"Potential near-duplicate workspaces require review: {len(duplicates)}",
        ]
    return runtime, result, prompt


def _hard_gate_assessment(
    workspace: DocumentGraphWorkspace,
    research: ResearchItem,
    extracted: ExtractedDocument,
):
    return evaluate_paper_fit(
        PaperFitAssessment(
            hard_gates=PaperFitHardGates(
                readable_content=False,
                has_title=bool(research.title.strip()),
                has_provenance=bool(workspace.content_hash and workspace.attachment_id),
                content_valid=False,
            ),
            dimensions=_zero_dimensions(),
            limitations=[item["message"] for item in extracted.limitations],
            reasoning_summary="No readable text layer was available for semantic evaluation.",
            confidence=1,
        )
    )


def _save_evaluation(
    db: Session,
    workspace: DocumentGraphWorkspace,
    result,
    runtime,
    input_hash: str,
) -> PaperEvaluation:
    record = db.scalar(select(PaperEvaluation).where(PaperEvaluation.workspace_id == workspace.id))
    values = {
        "rubric_version": result.rubric_version,
        "dimension_scores": result.dimensions.model_dump(),
        "fit_score": result.fit_score,
        "decision": result.decision,
        "failed_gates": result.failed_gates,
        "matched_pillars": result.matched_pillars,
        "candidate_parents": result.candidate_parents,
        "contribution_types": result.contribution_types,
        "overlaps_with": result.overlaps_with,
        "fills_gaps": result.fills_gaps,
        "limitations": result.limitations,
        "reasoning_summary": result.reasoning_summary,
        "confidence": result.confidence,
        "provider_name": workspace.provider_name if runtime else None,
        "model_name": runtime.name if runtime else None,
        "prompt_version": PAPER_FIT_PROMPT_VERSION,
        "input_hash": input_hash,
    }
    if record is None:
        record = PaperEvaluation(workspace_id=workspace.id, **values)
        db.add(record)
    else:
        for name, value in values.items():
            setattr(record, name, value)
    db.flush()
    return record


def _save_ai_output(
    db: Session,
    research_id: str,
    task: str,
    runtime,
    prompt_version: str,
    input_hash: str,
    output: dict,
    confidence: float,
) -> None:
    db.add(
        AIOutput(
            research_id=research_id,
            task=task,
            model_name=runtime.name,
            model_version=runtime.version,
            prompt_version=prompt_version,
            input_hash=input_hash,
            output_json=output,
            confidence=confidence,
        )
    )


def _validation_issue_summary(exc: ValidationError) -> str:
    issues: list[str] = []
    for error in exc.errors(
        include_input=False,
        include_context=False,
        include_url=False,
    )[:10]:
        location = ".".join(str(part) for part in error["loc"]) or "graph"
        issues.append(f"- {error['type']} at {location}")
    return "\n".join(issues)


def _complete_document_graph_with_recovery(
    runtime,
    title: str,
    extracted: ExtractedDocument,
    job_id: str,
) -> DocumentGraphExtraction:
    prompt = document_graph_prompt(title, extracted)
    try:
        with provider_observation(
            provider=runtime.version.split("-", 1)[0],
            model=runtime.name,
            operation="document-graph",
        ):
            return runtime.complete_json(prompt, DocumentGraphExtraction)
    except ValidationError as first_error:
        issue_count = first_error.error_count()
        logger.warning(
            "Retrying invalid structured document graph",
            extra={
                "job_id": job_id,
                "model": runtime.name,
                "action": "document.graph.recovery.scheduled",
                "validation_issue_count": issue_count,
            },
        )
        recovery_prompt = (
            f"{prompt}\n\n"
            "The previous response failed server-side validation. Return a complete replacement "
            "object, not a patch. Keep all node local_id values unique. Every parent, source, and "
            "target ID must reference a node in the same response. Do not create self-parent links "
            "or self-loop edges. Respect all list, string, confidence, and evidence bounds. "
            "Validation issue locations and categories:\n"
            f"{_validation_issue_summary(first_error)}"
        )
        try:
            with provider_observation(
                provider=runtime.version.split("-", 1)[0],
                model=runtime.name,
                operation="document-graph-recovery",
            ):
                recovered = runtime.complete_json(recovery_prompt, DocumentGraphExtraction)
        except ValidationError as recovery_error:
            logger.warning(
                "Structured document graph recovery failed",
                extra={
                    "job_id": job_id,
                    "model": runtime.name,
                    "action": "document.graph.recovery.failed",
                    "validation_issue_count": recovery_error.error_count(),
                },
            )
            raise
        logger.info(
            "Structured document graph recovered",
            extra={
                "job_id": job_id,
                "model": runtime.name,
                "validation_issue_count": issue_count,
                "action": "document.graph.recovery.completed",
            },
        )
        return recovered


def process_document(
    db: Session,
    workspace: DocumentGraphWorkspace,
    storage: ObjectStorage | None = None,
) -> DocumentGraphWorkspace:
    job_id = workspace.id
    storage = storage or get_object_storage()
    runtime = None
    try:
        attachment = db.get(Attachment, workspace.attachment_id)
        research = db.get(ResearchItem, workspace.research_id)
        if attachment is None or research is None:
            raise DocumentProcessingError(
                "DOCUMENT_EXTRACTION_FAILED", "Document metadata is incomplete"
            )

        _set_stage(db, workspace, "extracting")
        extracted = asyncio.run(extract_document(storage, workspace, attachment))
        workspace.extraction_limitations = extracted.limitations
        workspace.extracted_char_count = len(extracted.text)
        # A saved source version invalidates every graph fact derived from the
        # previous bytes. Clear it before evaluation so even a low-fit or failed
        # rebuild cannot expose stale evidence.
        clear_document_graph(db, workspace.id)
        research.content = extracted.text
        research.metadata_json = {
            **(research.metadata_json or {}),
            "document_extraction": extracted.metadata,
        }
        input_hash = hashlib.sha256(f"{research.title}\n{extracted.text}".encode()).hexdigest()

        _set_stage(db, workspace, "evaluating")
        if extracted.text.strip():
            runtime, result, _ = _provider_assessment(db, workspace, research, extracted)
            workspace.model_name = runtime.name
        else:
            result = _hard_gate_assessment(workspace, research, extracted)
        _save_evaluation(db, workspace, result, runtime, input_hash)
        if runtime:
            _save_ai_output(
                db,
                research.id,
                "paper-fit",
                runtime,
                PAPER_FIT_PROMPT_VERSION,
                input_hash,
                result.model_dump(mode="json"),
                result.confidence,
            )
        db.commit()

        graph_node_count = 0
        graph_edge_count = 0
        # The document graph is an isolated analysis workspace, not canonical publication.
        # Every readable source receives one. When paper-fit routed it to not_relevant, only the
        # server-built structure (document and sections) is kept: the semantic extraction call
        # would re-send up to 50k characters for nodes nobody is expected to review.
        if extracted.text.strip() and runtime is not None:
            _set_stage(db, workspace, "graph_building")
            skip_semantic = (
                settings.document_graph_skip_low_fit and result.decision == "not_relevant"
            )
            if skip_semantic:
                semantic = DocumentGraphExtraction()
            else:
                semantic = _complete_document_graph_with_recovery(
                    runtime,
                    research.title,
                    extracted,
                    job_id,
                )
            graph_node_count, graph_edge_count, limitations = replace_document_graph(
                db, workspace, research.title, extracted, semantic
            )
            if skip_semantic:
                limitations = [
                    *limitations,
                    {
                        "code": "GRAPH_SEMANTIC_SKIPPED_LOW_FIT",
                        "message": (
                            "Chỉ dựng cấu trúc tài liệu, không trích xuất khái niệm bằng AI vì "
                            "paper-fit xếp tài liệu vào nhóm không liên quan."
                        ),
                    },
                ]
            workspace.extraction_limitations = limitations
            if not skip_semantic:
                _save_ai_output(
                    db,
                    research.id,
                    "document-graph",
                    runtime,
                    DOCUMENT_GRAPH_PROMPT_VERSION,
                    input_hash,
                    semantic.model_dump(mode="json"),
                    result.confidence,
                )

        # RAG is an independently rebuildable projection. A provider failure is
        # recorded on the workspace but must not discard successful extraction,
        # evaluation or document-graph work.
        refresh_document_rag(db, workspace)

        workspace.processing_status = "needs_review"
        workspace.review_status = "needs_review"
        workspace.next_attempt_at = None
        workspace.finished_at = utcnow()
        workspace.error_code = None
        workspace.error_message = None
        db.add(
            AuditEvent(
                entity_type="document_workspace",
                entity_id=workspace.id,
                action="document.processed",
                payload={
                    "decision": result.decision,
                    "fit_score": result.fit_score,
                    "graph_node_count": graph_node_count,
                    "graph_edge_count": graph_edge_count,
                },
            )
        )
        db.commit()
        db.refresh(workspace)
        logger.info(
            "Document job completed",
            extra={"job_id": job_id, "decision": result.decision},
        )
    except Exception as exc:
        db.rollback()
        workspace = db.get(DocumentGraphWorkspace, job_id)
        if workspace:
            error = document_processing_error(exc, workspace.processing_status)
            if error.code == "INTERNAL_ERROR":
                # Bộ định dạng JSON bỏ exc_info; kiểu ngoại lệ và vị trí mã là phần an toàn để ghi.
                logger.error(
                    "Document job failed",
                    extra={
                        "action": "worker.document.failed",
                        "job_id": job_id,
                        **exception_fields(exc),
                    },
                )
            else:
                logger.warning(
                    "Document job did not complete",
                    extra={"job_id": job_id, "error_code": error.code},
                )
            workspace.error_code = error.code
            workspace.error_message = error.message[:2000]
            if error.retryable and workspace.attempt_count < settings.document_worker_max_attempts:
                workspace.processing_status = "queued"
                delay = settings.document_worker_retry_base_seconds * (
                    2 ** (workspace.attempt_count - 1)
                )
                workspace.next_attempt_at = utcnow() + timedelta(seconds=delay)
            else:
                workspace.processing_status = "failed"
                workspace.review_status = "not_requested"
                workspace.next_attempt_at = None
                workspace.finished_at = utcnow()
            db.commit()
    return workspace


def document_processing_error(exc: Exception, stage: str | None = None):
    if isinstance(exc, DocumentProcessingError):
        return exc
    if isinstance(exc, DocumentError):
        return DocumentProcessingError(exc.code, exc.message, exc.status_code >= 500)
    if stage in {"evaluating", "graph_building"}:
        if isinstance(exc, HTTPException):
            return DocumentProcessingError(
                "AI_PROVIDER_UNAVAILABLE",
                "The selected AI provider is not configured or available",
                exc.status_code >= 500,
            )
        if isinstance(exc, httpx.HTTPStatusError):
            code = exc.response.status_code
            if code in {401, 403}:
                return DocumentProcessingError(
                    "AI_PROVIDER_AUTH_FAILED",
                    "The AI provider rejected its configured credentials",
                )
            if code == 429:
                return DocumentProcessingError(
                    "AI_PROVIDER_RATE_LIMITED",
                    "The AI provider rate limit was reached",
                    True,
                )
            return DocumentProcessingError(
                "PAPER_EVALUATION_FAILED",
                "The AI provider could not complete document analysis",
                code >= 500,
            )
        if isinstance(exc, httpx.RequestError):
            return DocumentProcessingError(
                "AI_PROVIDER_UNAVAILABLE", "The AI provider could not be reached", True
            )
        if isinstance(exc, ValidationError | KeyError | ValueError):
            return DocumentProcessingError(
                "AI_RESPONSE_INVALID",
                "The AI provider returned invalid structured document analysis",
            )
    return DocumentProcessingError("INTERNAL_ERROR", "The document could not be processed")


def claim_next_document(db: Session) -> DocumentGraphWorkspace | None:
    now = utcnow()
    ready = and_(
        DocumentGraphWorkspace.processing_status.in_({"uploaded", "queued"}),
        or_(
            DocumentGraphWorkspace.next_attempt_at.is_(None),
            DocumentGraphWorkspace.next_attempt_at <= now,
        ),
    )
    expired = and_(
        DocumentGraphWorkspace.processing_status.in_(
            {"processing", "extracting", "evaluating", "graph_building"}
        ),
        DocumentGraphWorkspace.next_attempt_at.is_not(None),
        DocumentGraphWorkspace.next_attempt_at <= now,
    )
    # Không nhận lại vô hạn tác vụ đã làm worker dừng giữa chừng quá số lượt cho phép.
    db.execute(
        update(DocumentGraphWorkspace)
        .where(
            expired,
            DocumentGraphWorkspace.attempt_count >= settings.document_worker_max_attempts,
        )
        .values(
            processing_status="failed",
            review_status="not_requested",
            error_code="WORKER_LEASE_EXPIRED",
            error_message="The worker stopped before this job finished",
            next_attempt_at=None,
            finished_at=now,
        )
        .execution_options(synchronize_session=False)
    )
    item = db.scalar(
        select(DocumentGraphWorkspace)
        .where(or_(ready, expired))
        .order_by(DocumentGraphWorkspace.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if item is None:
        db.commit()
        return None
    item.processing_status = "processing"
    item.attempt_count += 1
    item.error_code = None
    item.error_message = None
    item.started_at = now
    item.finished_at = None
    item.next_attempt_at = now + timedelta(seconds=settings.document_worker_lease_seconds)
    item.provider_name = item.provider_name or settings.ai_provider
    db.commit()
    db.refresh(item)
    return item


def run_pending_documents(
    db: Session, max_jobs: int = 5, storage: ObjectStorage | None = None
) -> int:
    processed = 0
    while processed < max_jobs:
        item = claim_next_document(db)
        if item is None:
            break
        started = time.monotonic()
        result = process_document(db, item, storage)
        outcome = (
            "success"
            if result.processing_status == "needs_review"
            else "retry"
            if result.processing_status == "queued"
            else "error"
        )
        duration_seconds = time.monotonic() - started
        observe_worker_job(
            job_type="document-processing",
            outcome=outcome,
            error_code=result.error_code,
            duration_seconds=duration_seconds,
        )
        logger.info(
            "Worker job completed",
            extra={
                "action": "worker.job.completed",
                "job_id": result.id,
                "job_type": "document-processing",
                "stage": result.processing_status,
                "outcome": outcome,
                "error_code": result.error_code,
                "duration_ms": round(duration_seconds * 1000, 2),
            },
        )
        processed += 1
    return processed


def enqueue_document(
    db: Session, workspace: DocumentGraphWorkspace, provider_name: str | None = None
) -> DocumentGraphWorkspace:
    if workspace.processing_status not in {"uploaded", "failed"}:
        raise DocumentError(
            "DOCUMENT_STATE_CONFLICT",
            f"Document cannot be queued in status {workspace.processing_status}",
            409,
        )
    if provider_name and provider_name not in PROVIDERS:
        raise DocumentError("AI_PROVIDER_UNSUPPORTED", "Unsupported AI provider", 422)
    chosen = provider_name or workspace.provider_name or settings.ai_provider
    ensure_owner_spends(chosen, workspace.requested_by)
    workspace.processing_status = "queued"
    workspace.review_status = "not_requested"
    workspace.attempt_count = 0
    workspace.next_attempt_at = utcnow()
    workspace.started_at = None
    workspace.finished_at = None
    workspace.error_code = None
    workspace.error_message = None
    workspace.provider_name = chosen
    db.commit()
    db.refresh(workspace)
    return workspace


def graph_counts(db: Session, workspace_id: str) -> tuple[int, int]:
    nodes = int(
        db.scalar(
            select(func.count())
            .select_from(DocumentGraphNode)
            .where(DocumentGraphNode.workspace_id == workspace_id)
        )
        or 0
    )
    edges = int(
        db.scalar(
            select(func.count())
            .select_from(DocumentGraphEdge)
            .where(DocumentGraphEdge.workspace_id == workspace_id)
        )
        or 0
    )
    return nodes, edges
