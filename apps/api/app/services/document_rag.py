from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import (
    AuditEvent,
    DocumentGraphWorkspace,
    ResearchItem,
    SearchVectorProjection,
    utcnow,
)
from app.schemas.documents import DocumentRagStatusRead
from app.schemas.search import SearchDocument
from app.services.object_storage import DocumentError
from app.services.search_projection import (
    EmbeddingClient,
    PgvectorProjection,
    SearchProjectionError,
    embedding_client_from_settings,
)


def serialize_rag_status(workspace: DocumentGraphWorkspace) -> DocumentRagStatusRead:
    return DocumentRagStatusRead(
        status=workspace.rag_status,
        chunk_count=workspace.rag_chunk_count,
        indexed_version=workspace.rag_indexed_version,
        error_code=workspace.rag_error_code,
        indexed_at=workspace.rag_indexed_at,
    )


def _search_document(research: ResearchItem) -> SearchDocument:
    timestamp = research.updated_at or research.created_at or utcnow()
    return SearchDocument(
        id=research.id,
        display_id=research.display_id or research.id,
        title=research.title,
        summary=research.summary or "",
        content=research.content,
        type=research.type,
        collection_method=research.collection_method,
        authors=research.authors or [],
        tags=[tag.display_name for tag in research.tags],
        tag_keys=[tag.name for tag in research.tags],
        source_url=research.source_url,
        created_at=research.created_at or timestamp,
        updated_at=timestamp,
        # SearchDocument is shared with the approved projection. For a scoped
        # draft this timestamp is metadata only and does not grant approval.
        approved_at=research.approved_at or timestamp,
    )


def refresh_document_rag(
    db: Session,
    workspace: DocumentGraphWorkspace,
    *,
    embedding_factory: Callable[[], EmbeddingClient] = embedding_client_from_settings,
    raise_on_error: bool = False,
) -> DocumentRagStatusRead:
    workspace.rag_status = "indexing"
    workspace.rag_error_code = None
    db.commit()
    try:
        research = db.get(ResearchItem, workspace.research_id)
        if research is None:
            raise SearchProjectionError(
                "DOCUMENT_RAG_SOURCE_MISSING", "The document RAG source is unavailable."
            )
        if not (research.content or "").strip():
            db.execute(
                delete(SearchVectorProjection).where(
                    SearchVectorProjection.research_id == research.id
                )
            )
            chunk_count = 0
        else:
            chunk_count = PgvectorProjection(embedding_factory()).replace_document(
                db, _search_document(research)
            )
        workspace = db.get(DocumentGraphWorkspace, workspace.id)
        assert workspace is not None
        workspace.rag_status = "ready"
        workspace.rag_chunk_count = chunk_count
        workspace.rag_indexed_version = workspace.source_version
        workspace.rag_indexed_at = utcnow()
        workspace.rag_error_code = None
        db.add(
            AuditEvent(
                entity_type="document_workspace",
                entity_id=workspace.id,
                action="document.rag.ready",
                payload={
                    "source_version": workspace.source_version,
                    "chunk_count": chunk_count,
                },
            )
        )
        db.commit()
        db.refresh(workspace)
        return serialize_rag_status(workspace)
    except SearchProjectionError as exc:
        db.rollback()
        current = db.get(DocumentGraphWorkspace, workspace.id)
        if current is None:
            raise DocumentError("DOCUMENT_NOT_FOUND", "Document workspace not found", 404) from exc
        current.rag_status = "failed"
        current.rag_error_code = exc.code
        current.rag_chunk_count = 0
        db.add(
            AuditEvent(
                entity_type="document_workspace",
                entity_id=current.id,
                action="document.rag.failed",
                payload={"source_version": current.source_version, "error_code": exc.code},
            )
        )
        db.commit()
        if raise_on_error:
            raise DocumentError(exc.code, exc.message, exc.status_code) from exc
        return serialize_rag_status(current)
