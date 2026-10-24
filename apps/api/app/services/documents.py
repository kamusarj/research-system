import codecs
import logging
import uuid
from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path

from fastapi import UploadFile
from minio import Minio
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.localization import product_error_message
from app.core.observability import exception_fields
from app.models import (
    AIOutput,
    Attachment,
    AuditEvent,
    ChatMessage,
    ChatSession,
    Comment,
    DiscoveredItem,
    DocumentAIEditProposal,
    DocumentGraphEdge,
    DocumentGraphNode,
    DocumentGraphWorkspace,
    DocumentSourceVersion,
    EmbeddingChunk,
    Evaluation,
    GraphChangeSet,
    GraphMutation,
    IntakeReceiptItem,
    KnowledgeGap,
    LinkSubmission,
    NodeEvidence,
    OutboxEvent,
    PaperEvaluation,
    ResearchItem,
    ResearchRelation,
    ResearchVersion,
    SearchVectorProjection,
    research_tags,
)
from app.schemas.documents import DocumentContentRead, DocumentWorkspaceRead, PaperEvaluationRead
from app.services.document_graph import _extract_docx, read_stored_object
from app.services.object_storage import (
    DocumentError,
    LocalObjectStorage,
    MinioObjectStorage,
    ObjectStorage,
    RoutedObjectStorage,
    StoredObject,
)

logger = logging.getLogger("research-api.documents")

ALLOWED_DOCUMENT_TYPES: dict[str, set[str]] = {
    ".pdf": {"application/pdf", "application/octet-stream"},
    ".md": {"text/markdown", "text/plain", "application/octet-stream"},
    ".markdown": {"text/markdown", "text/plain", "application/octet-stream"},
    ".txt": {"text/plain", "application/octet-stream"},
    ".tex": {"application/x-tex", "text/x-tex", "text/plain", "application/octet-stream"},
    ".latex": {"application/x-tex", "text/x-tex", "text/plain", "application/octet-stream"},
    ".rst": {"text/x-rst", "text/plain", "application/octet-stream"},
    ".adoc": {"text/asciidoc", "text/plain", "application/octet-stream"},
    ".asciidoc": {"text/asciidoc", "text/plain", "application/octet-stream"},
    ".html": {"text/html", "application/xhtml+xml", "application/octet-stream"},
    ".htm": {"text/html", "application/xhtml+xml", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
}
SOURCE_TEXT_SUFFIXES = {
    ".md",
    ".markdown",
    ".txt",
    ".tex",
    ".latex",
    ".rst",
    ".adoc",
    ".asciidoc",
    ".html",
    ".htm",
}
EDITABLE_SOURCE_SUFFIXES = SOURCE_TEXT_SUFFIXES
BINARY_DOCUMENT_SUFFIXES = {".pdf", ".docx"}
PREVIEW_KIND_BY_SUFFIX = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".tex": "latex",
    ".latex": "latex",
    ".rst": "markup",
    ".adoc": "markup",
    ".asciidoc": "markup",
    ".html": "html",
    ".htm": "html",
    ".docx": "docx",
    ".pdf": "pdf",
    ".txt": "plain",
}
ACTIVE_DOCUMENT_STATUSES = frozenset(
    {"uploaded", "queued", "processing", "extracting", "evaluating", "graph_building"}
)


def _document_summary(research: ResearchItem) -> str:
    source = research.summary or research.content or ""
    return " ".join(source.split())[:500]


def _secret(value) -> str | None:
    if value is None:
        return None
    configured = value.get_secret_value().strip()
    return configured or None


def build_object_storage(config=settings) -> ObjectStorage:
    local = LocalObjectStorage(config.document_storage_dir, config.document_max_upload_bytes)
    access_key = _secret(config.minio_access_key)
    secret_key = _secret(config.minio_secret_key)
    if bool(access_key) != bool(secret_key):
        raise DocumentError(
            "DOCUMENT_STORAGE_FAILED",
            "MinIO access and secret keys must be configured together",
            503,
        )
    remote = None
    if access_key and secret_key:
        remote = MinioObjectStorage(
            Minio(
                config.minio_endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=config.minio_secure,
                region=config.minio_region,
            ),
            config.minio_bucket,
            config.document_max_upload_bytes,
            auto_create_bucket=config.minio_auto_create_bucket,
            spool_memory_bytes=config.minio_spool_memory_bytes,
        )
    return RoutedObjectStorage(local, remote, config.document_storage_backend)


@lru_cache(maxsize=1)
def get_object_storage() -> ObjectStorage:
    return build_object_storage()


def normalized_upload(filename: str | None, content_type: str | None) -> tuple[str, str, str]:
    safe_name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not safe_name or len(safe_name) > 500:
        raise DocumentError("INVALID_DOCUMENT_NAME", "Document filename is invalid")
    suffix = Path(safe_name).suffix.casefold()
    if suffix not in ALLOWED_DOCUMENT_TYPES:
        raise DocumentError(
            "UNSUPPORTED_DOCUMENT_TYPE",
            (
                "Supported documents are PDF, DOCX, UTF-8 text, Markdown, LaTeX, "
                "reStructuredText, AsciiDoc and HTML"
            ),
            415,
        )
    mime_type = (content_type or "application/octet-stream").split(";", 1)[0].casefold()
    if mime_type not in ALLOWED_DOCUMENT_TYPES[suffix]:
        raise DocumentError(
            "UNSUPPORTED_DOCUMENT_TYPE",
            f"MIME type {mime_type} does not match the {suffix} extension",
            415,
        )
    return safe_name, suffix, mime_type


async def validated_upload_chunks(upload: UploadFile, suffix: str) -> AsyncIterator[bytes]:
    first = True
    decoder = (
        codecs.getincrementaldecoder("utf-8")("strict")
        if suffix not in BINARY_DOCUMENT_SUFFIXES
        else None
    )
    try:
        while chunk := await upload.read(64 * 1024):
            if first and suffix == ".pdf" and not chunk.startswith(b"%PDF-"):
                raise DocumentError(
                    "UNSUPPORTED_DOCUMENT_TYPE", "The uploaded file is not a valid PDF", 415
                )
            if first and suffix == ".docx" and not chunk.startswith(b"PK\x03\x04"):
                raise DocumentError(
                    "UNSUPPORTED_DOCUMENT_TYPE",
                    "The uploaded file is not a valid DOCX container",
                    415,
                )
            first = False
            if decoder is not None:
                if b"\x00" in chunk:
                    raise DocumentError(
                        "UNSUPPORTED_DOCUMENT_TYPE", "Text documents cannot contain NUL bytes", 415
                    )
                try:
                    decoder.decode(chunk)
                except UnicodeDecodeError as exc:
                    raise DocumentError(
                        "UNSUPPORTED_DOCUMENT_TYPE", "Text documents must use UTF-8", 415
                    ) from exc
            yield chunk
        if first:
            raise DocumentError("UNSUPPORTED_DOCUMENT_TYPE", "The uploaded document is empty", 415)
        if decoder is not None:
            try:
                decoder.decode(b"", final=True)
            except UnicodeDecodeError as exc:
                raise DocumentError(
                    "UNSUPPORTED_DOCUMENT_TYPE", "Text documents must use UTF-8", 415
                ) from exc
    finally:
        await upload.close()


def serialize_document(db: Session, workspace: DocumentGraphWorkspace) -> DocumentWorkspaceRead:
    attachment = db.get(Attachment, workspace.attachment_id)
    research = db.get(ResearchItem, workspace.research_id)
    if attachment is None or research is None:
        raise DocumentError(
            "DOCUMENT_STORAGE_FAILED", "Document workspace metadata is incomplete", 500
        )
    evaluation = db.scalar(
        select(PaperEvaluation).where(PaperEvaluation.workspace_id == workspace.id)
    )
    graph_node_count = int(
        db.scalar(
            select(func.count())
            .select_from(DocumentGraphNode)
            .where(DocumentGraphNode.workspace_id == workspace.id)
        )
        or 0
    )
    graph_edge_count = int(
        db.scalar(
            select(func.count())
            .select_from(DocumentGraphEdge)
            .where(DocumentGraphEdge.workspace_id == workspace.id)
        )
        or 0
    )
    evaluation_read = None
    if evaluation is not None:
        evaluation_read = PaperEvaluationRead(
            id=evaluation.id,
            rubric_version=evaluation.rubric_version,
            dimension_scores=evaluation.dimension_scores or {},
            fit_score=evaluation.fit_score,
            decision=evaluation.decision,
            failed_gates=evaluation.failed_gates or [],
            matched_pillars=evaluation.matched_pillars or [],
            candidate_parents=evaluation.candidate_parents or [],
            contribution_types=evaluation.contribution_types or [],
            overlaps_with=evaluation.overlaps_with or [],
            fills_gaps=evaluation.fills_gaps or [],
            limitations=evaluation.limitations or [],
            reasoning_summary=evaluation.reasoning_summary,
            confidence=evaluation.confidence,
            provider_name=evaluation.provider_name,
            model_name=evaluation.model_name,
            prompt_version=evaluation.prompt_version,
            created_at=evaluation.created_at,
        )
    return DocumentWorkspaceRead(
        id=workspace.id,
        research_id=workspace.research_id,
        attachment_id=workspace.attachment_id,
        filename=attachment.filename,
        summary=_document_summary(research),
        mime_type=attachment.mime_type,
        size_bytes=attachment.size_bytes,
        content_hash=workspace.content_hash,
        processing_status=workspace.processing_status,
        review_status=workspace.review_status,
        extraction_limitations=[
            {
                **limitation,
                "message": product_error_message(str(limitation.get("code") or ""), 400),
            }
            for limitation in (workspace.extraction_limitations or [])
        ],
        error_code=workspace.error_code,
        error_message=(
            product_error_message(workspace.error_code, 500)
            if workspace.error_code
            else None
        ),
        provider_name=workspace.provider_name,
        model_name=workspace.model_name,
        attempt_count=workspace.attempt_count,
        next_attempt_at=workspace.next_attempt_at,
        started_at=workspace.started_at,
        finished_at=workspace.finished_at,
        extracted_char_count=workspace.extracted_char_count,
        graph_node_count=graph_node_count,
        graph_edge_count=graph_edge_count,
        source_version=workspace.source_version,
        editable=Path(attachment.filename).suffix.casefold()
        in EDITABLE_SOURCE_SUFFIXES | BINARY_DOCUMENT_SUFFIXES,
        rag_status=workspace.rag_status,
        rag_chunk_count=workspace.rag_chunk_count,
        rag_indexed_version=workspace.rag_indexed_version,
        rag_error_code=workspace.rag_error_code,
        rag_indexed_at=workspace.rag_indexed_at,
        evaluation=evaluation_read,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )


async def delete_document(
    db: Session,
    workspace: DocumentGraphWorkspace,
    storage: ObjectStorage,
) -> None:
    if workspace.processing_status in ACTIVE_DOCUMENT_STATUSES:
        raise DocumentError(
            "DOCUMENT_DELETE_IN_PROGRESS",
            "Wait for document processing to finish before deleting it",
            409,
        )
    if db.scalar(
        select(func.count())
        .select_from(IntakeReceiptItem)
        .where(IntakeReceiptItem.document_workspace_id == workspace.id)
    ):
        raise DocumentError(
            "DOCUMENT_DELETE_PROVENANCE_LOCKED",
            "This document is retained by an intake receipt and cannot be deleted",
            409,
        )

    change_sets = list(
        db.scalars(
            select(GraphChangeSet).where(
                GraphChangeSet.origin_type == "document",
                GraphChangeSet.origin_id == workspace.id,
            )
        )
    )
    if any(item.lifecycle_status == "applied" for item in change_sets):
        raise DocumentError(
            "DOCUMENT_DELETE_PROVENANCE_LOCKED",
            "This document has an applied graph change and cannot be deleted",
            409,
        )

    attachment = db.get(Attachment, workspace.attachment_id)
    research = db.get(ResearchItem, workspace.research_id)
    if attachment is None or research is None:
        raise DocumentError(
            "DOCUMENT_STORAGE_FAILED", "Document workspace metadata is incomplete", 500
        )

    source_versions = list(
        db.scalars(
            select(DocumentSourceVersion).where(
                DocumentSourceVersion.workspace_id == workspace.id
            )
        )
    )
    object_keys = {
        attachment.object_key,
        workspace.storage_object_key,
        *(version.object_key for version in source_versions),
    }
    node_ids = list(
        db.scalars(
            select(DocumentGraphNode.id).where(DocumentGraphNode.workspace_id == workspace.id)
        )
    )
    edge_ids = list(
        db.scalars(
            select(DocumentGraphEdge.id).where(DocumentGraphEdge.workspace_id == workspace.id)
        )
    )
    session_ids = list(
        db.scalars(
            select(ChatSession.id).where(
                ChatSession.scope_type == "document", ChatSession.scope_id == workspace.id
            )
        )
    )
    change_set_ids = [item.id for item in change_sets]

    db.add(
        AuditEvent(
            entity_type="document_workspace",
            entity_id=workspace.id,
            action="document.deleted",
            payload={
                "research_id": research.id,
                "filename": attachment.filename,
                "content_hash": workspace.content_hash,
                "object_count": len(object_keys),
            },
        )
    )

    db.execute(
        update(DiscoveredItem)
        .where(DiscoveredItem.research_id == research.id)
        .values(research_id=None)
    )
    db.execute(
        update(LinkSubmission)
        .where(LinkSubmission.research_id == research.id)
        .values(research_id=None)
    )
    db.execute(
        update(KnowledgeGap)
        .where(KnowledgeGap.deep_research_id == research.id)
        .values(deep_research_id=None)
    )
    if session_ids:
        db.execute(delete(ChatMessage).where(ChatMessage.session_id.in_(session_ids)))
        db.execute(delete(ChatSession).where(ChatSession.id.in_(session_ids)))
    if change_set_ids:
        db.execute(
            update(ChatMessage)
            .where(ChatMessage.linked_change_set_id.in_(change_set_ids))
            .values(linked_change_set_id=None)
        )
        db.execute(delete(GraphMutation).where(GraphMutation.change_set_id.in_(change_set_ids)))
        db.execute(delete(GraphChangeSet).where(GraphChangeSet.id.in_(change_set_ids)))
    owner_ids = node_ids + edge_ids
    if owner_ids:
        db.execute(delete(NodeEvidence).where(NodeEvidence.owner_id.in_(owner_ids)))
    db.execute(delete(NodeEvidence).where(NodeEvidence.source_document_id == research.id))
    db.execute(delete(DocumentGraphEdge).where(DocumentGraphEdge.workspace_id == workspace.id))
    db.execute(delete(DocumentGraphNode).where(DocumentGraphNode.workspace_id == workspace.id))
    db.execute(delete(PaperEvaluation).where(PaperEvaluation.workspace_id == workspace.id))
    db.execute(
        delete(DocumentAIEditProposal).where(DocumentAIEditProposal.workspace_id == workspace.id)
    )
    db.execute(
        delete(DocumentSourceVersion).where(DocumentSourceVersion.workspace_id == workspace.id)
    )
    db.execute(
        delete(SearchVectorProjection).where(SearchVectorProjection.research_id == research.id)
    )
    db.execute(delete(EmbeddingChunk).where(EmbeddingChunk.research_id == research.id))
    db.execute(delete(AIOutput).where(AIOutput.research_id == research.id))
    db.execute(delete(Evaluation).where(Evaluation.research_item_id == research.id))
    db.execute(
        delete(ResearchRelation).where(
            (ResearchRelation.source_id == research.id)
            | (ResearchRelation.target_id == research.id)
        )
    )
    db.execute(delete(ResearchVersion).where(ResearchVersion.research_id == research.id))
    db.execute(delete(Comment).where(Comment.research_id == research.id))
    db.execute(delete(research_tags).where(research_tags.c.research_id == research.id))
    db.execute(delete(OutboxEvent).where(OutboxEvent.aggregate_id == workspace.id))
    db.execute(delete(DocumentGraphWorkspace).where(DocumentGraphWorkspace.id == workspace.id))
    db.execute(delete(Attachment).where(Attachment.research_id == research.id))
    db.execute(delete(ResearchItem).where(ResearchItem.id == research.id))
    # Commit trước rồi mới xóa tệp: nếu xóa tệp lỗi, chỉ còn tệp mồ côi vô hại; làm ngược lại thì
    # lỗi commit để lại bản ghi trỏ tới tệp đã mất.
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    for object_key in sorted(object_keys):
        try:
            await storage.delete(object_key)
        except Exception as exc:
            logger.warning(
                "Document object could not be deleted after its records were removed",
                extra={
                    "action": "document.object_delete_failed",
                    "job_id": workspace.id,
                    **exception_fields(exc),
                },
            )


async def serialize_document_content(
    db: Session,
    workspace: DocumentGraphWorkspace,
    storage: ObjectStorage,
) -> DocumentContentRead:
    attachment = db.get(Attachment, workspace.attachment_id)
    research = db.get(ResearchItem, workspace.research_id)
    if attachment is None or research is None:
        raise DocumentError(
            "DOCUMENT_STORAGE_FAILED", "Document workspace metadata is incomplete", 500
        )
    suffix = Path(attachment.filename).suffix.casefold()
    source_text = None
    source_truncated = False
    editing_representation = "source"
    if suffix in SOURCE_TEXT_SUFFIXES or (
        suffix in BINARY_DOCUMENT_SUFFIXES and workspace.source_version > 1
    ):
        content = await read_stored_object(
            storage, workspace.storage_object_key, settings.document_max_upload_bytes
        )
        try:
            decoded = content.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError as exc:
            raise DocumentError(
                "DOCUMENT_EXTRACTION_FAILED", "Text document is not valid UTF-8"
            ) from exc
        source_truncated = len(decoded) > settings.document_extract_max_chars
        source_text = decoded[: settings.document_extract_max_chars]
    elif suffix in BINARY_DOCUMENT_SUFFIXES and research.content:
        source_truncated = len(research.content) > settings.document_extract_max_chars
        source_text = research.content[: settings.document_extract_max_chars]
    if suffix in BINARY_DOCUMENT_SUFFIXES:
        editing_representation = "extracted_text"
    extracted_text = (research.content or source_text or "")[: settings.document_extract_max_chars]
    return DocumentContentRead(
        workspace_id=workspace.id,
        filename=attachment.filename,
        format=suffix.removeprefix("."),
        preview_kind=PREVIEW_KIND_BY_SUFFIX.get(suffix, "plain"),
        source_text=source_text,
        extracted_text=extracted_text,
        supports_raw=source_text is not None,
        source_truncated=source_truncated,
        editable=suffix in EDITABLE_SOURCE_SUFFIXES or bool(source_text and source_text.strip()),
        source_version=workspace.source_version,
        editing_representation=editing_representation,
        original_available=suffix in BINARY_DOCUMENT_SUFFIXES,
        original_preview_kind="pdf" if suffix == ".pdf" else None,
    )


def add_document_records(
    db: Session,
    *,
    filename: str,
    mime_type: str,
    workspace_id: str,
    stored: StoredObject,
    provider_name: str | None = None,
) -> DocumentGraphWorkspace:
    research = ResearchItem(
        title=Path(filename).stem[:500],
        type="reference",
        status="draft",
        collection_method="upload",
        content="",
        authors=[],
        metadata_json={
            "document_workspace_id": workspace_id,
            "upload_content_hash": stored.sha256,
        },
    )
    db.add(research)
    db.flush()
    research.display_id = f"RES-UPLOAD-{research.id[:8].upper()}"
    attachment = Attachment(
        research_id=research.id,
        filename=filename,
        object_key=stored.key,
        mime_type=mime_type,
        size_bytes=stored.size_bytes,
    )
    db.add(attachment)
    db.flush()
    workspace = DocumentGraphWorkspace(
        id=workspace_id,
        research_id=research.id,
        attachment_id=attachment.id,
        storage_object_key=stored.key,
        content_hash=stored.sha256,
        processing_status="uploaded",
        review_status="not_requested",
        extraction_limitations=[],
        provider_name=provider_name or settings.ai_provider,
    )
    db.add(workspace)
    db.add(
        DocumentSourceVersion(
            workspace_id=workspace.id,
            version_number=1,
            object_key=stored.key,
            content_hash=stored.sha256,
            size_bytes=stored.size_bytes,
            origin="upload",
            change_summary="Initial uploaded source",
        )
    )
    db.add_all(
        [
            AuditEvent(
                entity_type="document_workspace",
                entity_id=workspace.id,
                action="document.uploaded",
                payload={"content_hash": stored.sha256, "size_bytes": stored.size_bytes},
            ),
            OutboxEvent(
                event_type="document.uploaded",
                aggregate_id=workspace.id,
                payload={"workspace_id": workspace.id},
            ),
        ]
    )
    db.flush()
    return workspace


async def create_document(
    db: Session, upload: UploadFile, storage: ObjectStorage
) -> DocumentGraphWorkspace:
    filename, suffix, mime_type = normalized_upload(upload.filename, upload.content_type)
    workspace_id = str(uuid.uuid4())
    object_key = f"documents/{workspace_id}/{uuid.uuid4().hex}{suffix}"
    stored = await storage.put(
        object_key,
        validated_upload_chunks(upload, suffix),
        {"filename": filename, "mime_type": mime_type},
    )
    if suffix == ".docx":
        try:
            content = await read_stored_object(
                storage, stored.key, settings.document_max_upload_bytes
            )
            _extract_docx(content, filename)
        except DocumentError as exc:
            await storage.delete(stored.key)
            raise DocumentError("UNSUPPORTED_DOCUMENT_TYPE", exc.message, 415) from exc
    duplicate = db.scalar(
        select(DocumentGraphWorkspace).where(DocumentGraphWorkspace.content_hash == stored.sha256)
    )
    if duplicate is not None:
        await storage.delete(stored.key)
        raise DocumentError(
            "DUPLICATE_DOCUMENT",
            f"This document already exists as workspace {duplicate.id}",
            409,
        )

    try:
        workspace = add_document_records(
            db,
            filename=filename,
            mime_type=mime_type,
            workspace_id=workspace_id,
            stored=stored,
        )
        db.commit()
        db.refresh(workspace)
        return workspace
    except IntegrityError as exc:
        db.rollback()
        await storage.delete(stored.key)
        raise DocumentError("DUPLICATE_DOCUMENT", "This document already exists", 409) from exc
    except Exception:
        db.rollback()
        await storage.delete(stored.key)
        raise
