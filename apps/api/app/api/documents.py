from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Attachment, DocumentGraphWorkspace, DocumentSourceVersion
from app.schemas.documents import (
    DocumentAIEditCreateRequest,
    DocumentAIEditRead,
    DocumentBrainstormRead,
    DocumentBrainstormRequest,
    DocumentContentRead,
    DocumentGraphRead,
    DocumentGraphResearchRead,
    DocumentGraphResearchRequest,
    DocumentInstantEditRead,
    DocumentInstantEditRequest,
    DocumentRagStatusRead,
    DocumentSourceRestoreRequest,
    DocumentSourceSaveRequest,
    DocumentSourceVersionList,
    DocumentSourceVersionRead,
    DocumentWorkspaceList,
    DocumentWorkspaceRead,
    LatexCompileRequest,
    PaperEvaluationRead,
)
from app.schemas.graph_changes import GraphChangeSetRead
from app.schemas.ingestion import AIProviderName
from app.services.document_brainstorm import brainstorm_document
from app.services.document_editing import (
    accept_ai_edit,
    create_source_version,
    list_source_versions,
    propose_ai_edit,
    reject_ai_edit,
    restore_source_version,
    serialize_version,
)
from app.services.document_graph import serialize_document_graph
from app.services.document_graph_research import research_document_graph
from app.services.document_instant_edit import instant_edit_document
from app.services.document_processing import enqueue_document
from app.services.document_rag import refresh_document_rag, serialize_rag_status
from app.services.documents import (
    create_document,
    delete_document,
    get_object_storage,
    serialize_document,
    serialize_document_content,
)
from app.services.graph_changes import serialize_change_set
from app.services.latex_compiler import compile_latex
from app.services.object_storage import DocumentError, ObjectStorage
from app.services.ontology_mapping import create_document_change_set

# Phòng thủ nhiều lớp cho tệp tải xuống: nếu trình duyệt vẫn hiển thị, nội dung bị cô lập.
DOWNLOAD_CSP = "sandbox; default-src 'none'"

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document(db: Session, document_id: str) -> DocumentGraphWorkspace:
    item = db.get(DocumentGraphWorkspace, document_id)
    if item is None:
        raise DocumentError("DOCUMENT_NOT_FOUND", "Document workspace not found", 404)
    return item


@router.post("", response_model=DocumentWorkspaceRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_object_storage),
) -> DocumentWorkspaceRead:
    return serialize_document(db, await create_document(db, file, storage))


@router.post("/brainstorm", response_model=DocumentBrainstormRead)
def document_brainstorm(request: DocumentBrainstormRequest) -> DocumentBrainstormRead:
    return brainstorm_document(request)


@router.post("/edit-in-place", response_model=DocumentInstantEditRead)
def document_instant_edit(request: DocumentInstantEditRequest) -> DocumentInstantEditRead:
    return instant_edit_document(request)


@router.post("/latex/compile", response_class=Response)
def compile_latex_preview(request: LatexCompileRequest) -> Response:
    return Response(
        content=compile_latex(request.source),
        media_type="application/pdf",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("", response_model=DocumentWorkspaceList)
def list_documents(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> DocumentWorkspaceList:
    items = list(
        db.scalars(
            select(DocumentGraphWorkspace)
            .order_by(DocumentGraphWorkspace.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return DocumentWorkspaceList(
        items=[serialize_document(db, item) for item in items],
        total=int(db.scalar(select(func.count()).select_from(DocumentGraphWorkspace)) or 0),
    )


@router.get("/{document_id}", response_model=DocumentWorkspaceRead)
def document(document_id: str, db: Session = Depends(get_db)) -> DocumentWorkspaceRead:
    return serialize_document(db, get_document(db, document_id))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_document(
    document_id: str,
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_object_storage),
) -> Response:
    await delete_document(db, get_document(db, document_id), storage)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{document_id}/content", response_model=DocumentContentRead)
async def document_content(
    document_id: str,
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_object_storage),
) -> DocumentContentRead:
    return await serialize_document_content(db, get_document(db, document_id), storage)


@router.get("/{document_id}/versions", response_model=DocumentSourceVersionList)
def document_versions(
    document_id: str,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> DocumentSourceVersionList:
    return list_source_versions(db, get_document(db, document_id), limit=limit)


@router.post(
    "/{document_id}/versions",
    response_model=DocumentSourceVersionRead,
    status_code=status.HTTP_201_CREATED,
)
async def save_document_source(
    document_id: str,
    payload: DocumentSourceSaveRequest,
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_object_storage),
) -> DocumentSourceVersionRead:
    workspace = get_document(db, document_id)
    version = await create_source_version(
        db,
        workspace,
        storage,
        base_version=payload.base_version,
        content=payload.content,
        origin="manual",
        change_summary=payload.change_summary,
    )
    return serialize_version(version, version.version_number)


@router.post(
    "/{document_id}/versions/{version_number}/restore",
    response_model=DocumentSourceVersionRead,
    status_code=status.HTTP_201_CREATED,
)
async def restore_document_source(
    document_id: str,
    version_number: int,
    payload: DocumentSourceRestoreRequest,
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_object_storage),
) -> DocumentSourceVersionRead:
    workspace = get_document(db, document_id)
    restored = await restore_source_version(
        db,
        workspace,
        storage,
        version_number,
        base_version=payload.base_version,
    )
    return serialize_version(restored, restored.version_number)


@router.post(
    "/{document_id}/ai-edits",
    response_model=DocumentAIEditRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_document_ai_edit(
    document_id: str,
    payload: DocumentAIEditCreateRequest,
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_object_storage),
) -> DocumentAIEditRead:
    return await propose_ai_edit(db, get_document(db, document_id), storage, payload)


@router.post(
    "/{document_id}/ai-edits/{proposal_id}/accept",
    response_model=DocumentAIEditRead,
)
async def accept_document_ai_edit(
    document_id: str,
    proposal_id: str,
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_object_storage),
) -> DocumentAIEditRead:
    return await accept_ai_edit(db, get_document(db, document_id), proposal_id, storage)


@router.post(
    "/{document_id}/ai-edits/{proposal_id}/reject",
    response_model=DocumentAIEditRead,
)
async def reject_document_ai_edit(
    document_id: str,
    proposal_id: str,
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_object_storage),
) -> DocumentAIEditRead:
    return await reject_ai_edit(db, get_document(db, document_id), proposal_id, storage)


@router.get("/{document_id}/rag", response_model=DocumentRagStatusRead)
def document_rag_status(document_id: str, db: Session = Depends(get_db)) -> DocumentRagStatusRead:
    return serialize_rag_status(get_document(db, document_id))


@router.post("/{document_id}/rag/rebuild", response_model=DocumentRagStatusRead)
def rebuild_document_rag(document_id: str, db: Session = Depends(get_db)) -> DocumentRagStatusRead:
    return refresh_document_rag(db, get_document(db, document_id), raise_on_error=True)


@router.post("/{document_id}/analyze", response_model=DocumentWorkspaceRead, status_code=202)
def analyze_document(
    document_id: str,
    provider: AIProviderName | None = None,
    db: Session = Depends(get_db),
) -> DocumentWorkspaceRead:
    workspace = get_document(db, document_id)
    return serialize_document(db, enqueue_document(db, workspace, provider))


@router.post("/{document_id}/retry", response_model=DocumentWorkspaceRead, status_code=202)
def retry_document(
    document_id: str,
    provider: AIProviderName | None = None,
    db: Session = Depends(get_db),
) -> DocumentWorkspaceRead:
    workspace = get_document(db, document_id)
    if workspace.processing_status != "failed":
        raise DocumentError(
            "DOCUMENT_STATE_CONFLICT",
            f"Document cannot be retried in status {workspace.processing_status}",
            409,
        )
    return serialize_document(db, enqueue_document(db, workspace, provider))


@router.get("/{document_id}/evaluation", response_model=PaperEvaluationRead)
def document_evaluation(document_id: str, db: Session = Depends(get_db)) -> PaperEvaluationRead:
    workspace = get_document(db, document_id)
    serialized = serialize_document(db, workspace)
    if serialized.evaluation is None:
        raise DocumentError("PAPER_EVALUATION_NOT_READY", "Paper evaluation is not ready", 404)
    return serialized.evaluation


@router.get("/{document_id}/graph", response_model=DocumentGraphRead)
def document_graph(document_id: str, db: Session = Depends(get_db)) -> DocumentGraphRead:
    workspace = get_document(db, document_id)
    return serialize_document_graph(db, workspace.id)


@router.post("/{document_id}/graph/research", response_model=DocumentGraphResearchRead)
def document_graph_research(
    document_id: str,
    request: DocumentGraphResearchRequest,
    db: Session = Depends(get_db),
) -> DocumentGraphResearchRead:
    workspace = get_document(db, document_id)
    graph, change_set = research_document_graph(db, workspace, request)
    return DocumentGraphResearchRead(
        graph=graph,
        change_set=serialize_change_set(db, change_set) if change_set else None,
    )


@router.post(
    "/{document_id}/create-change-set",
    response_model=GraphChangeSetRead,
    status_code=201,
)
def document_change_set(document_id: str, db: Session = Depends(get_db)) -> GraphChangeSetRead:
    workspace = get_document(db, document_id)
    return serialize_change_set(db, create_document_change_set(db, workspace))


@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_object_storage),
) -> StreamingResponse:
    workspace = get_document(db, document_id)
    attachment = db.get(Attachment, workspace.attachment_id)
    if attachment is None:
        raise DocumentError(
            "DOCUMENT_STORAGE_FAILED", "Document attachment metadata is missing", 500
        )
    suffix = attachment.filename.rsplit(".", 1)[-1].casefold()
    object_key = workspace.storage_object_key
    if suffix in {"pdf", "docx"}:
        initial = db.scalar(
            select(DocumentSourceVersion).where(
                DocumentSourceVersion.workspace_id == workspace.id,
                DocumentSourceVersion.version_number == 1,
            )
        )
        if initial is None:
            raise DocumentError(
                "DOCUMENT_STORAGE_FAILED", "Original document version is missing", 500
            )
        object_key = initial.object_key
    encoded_name = quote(attachment.filename, safe="")
    return StreamingResponse(
        storage.open(object_key),
        media_type=attachment.mime_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": DOWNLOAD_CSP,
        },
    )


@router.get("/{document_id}/original")
def original_document(
    document_id: str,
    inline: bool = Query(False),
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_object_storage),
) -> StreamingResponse:
    workspace = get_document(db, document_id)
    attachment = db.get(Attachment, workspace.attachment_id)
    if attachment is None:
        raise DocumentError(
            "DOCUMENT_STORAGE_FAILED", "Document attachment metadata is missing", 500
        )
    initial = db.scalar(
        select(DocumentSourceVersion).where(
            DocumentSourceVersion.workspace_id == workspace.id,
            DocumentSourceVersion.version_number == 1,
        )
    )
    if initial is None:
        raise DocumentError("DOCUMENT_STORAGE_FAILED", "Original document version is missing", 500)
    encoded_name = quote(attachment.filename, safe="")
    # Tệp tải lên được phục vụ cùng origin với ứng dụng: chỉ PDF được hiển thị trực tiếp. HTML/SVG
    # do người khác tải lên mà mở inline sẽ chạy script bằng phiên của người xem.
    show_inline = inline and attachment.mime_type == "application/pdf"
    headers = {
        "Content-Disposition": (
            f"{'inline' if show_inline else 'attachment'}; filename*=UTF-8''{encoded_name}"
        ),
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-store",
    }
    if not show_inline:
        headers["Content-Security-Policy"] = DOWNLOAD_CSP
    return StreamingResponse(
        storage.open(initial.object_key),
        media_type=attachment.mime_type,
        headers=headers,
    )
