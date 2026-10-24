from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ChatMessage, ChatSession
from app.schemas.chat import (
    ChatGPTSharedImportRequest,
    ChatMessageRead,
    ChatModelsRead,
    ChatModelsRequest,
    ChatSessionCreate,
    ChatSessionList,
    ChatSessionRead,
    ChatSummaryRequest,
    ChatTurnRead,
    ChatTurnRequest,
    ChatVerificationRead,
    ChatVerifyRequest,
)
from app.services.chat_connections import list_personal_models, verify_personal_model
from app.services.documents import get_object_storage
from app.services.graph_chat import (
    close_chat_session,
    create_chat_session,
    create_chatgpt_import_session,
    get_chat_session,
    list_chat_messages,
    run_chat_turn,
    serialize_chat_message,
    serialize_chat_session,
    summarize_chat_session,
)
from app.services.object_storage import DocumentError, ObjectStorage
from app.services.providers.openai_graph_chat import graph_chat_provider

router = APIRouter(prefix="/chat", tags=["graph-chat"])


@router.post("/connections/models", response_model=ChatModelsRead)
def connection_models(request: ChatModelsRequest, response: Response) -> ChatModelsRead:
    response.headers["Cache-Control"] = "no-store"
    return list_personal_models(request)


@router.post("/connections/verify", response_model=ChatVerificationRead)
def connection_verify(request: ChatVerifyRequest, response: Response) -> ChatVerificationRead:
    response.headers["Cache-Control"] = "no-store"
    return verify_personal_model(request)


@router.get("/sessions", response_model=ChatSessionList)
def sessions(
    status: str | None = Query(default=None, max_length=30),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ChatSessionList:
    statement = select(ChatSession).order_by(ChatSession.updated_at.desc()).limit(limit)
    count_statement = select(func.count()).select_from(ChatSession)
    if status:
        statement = statement.where(ChatSession.status == status)
        count_statement = count_statement.where(ChatSession.status == status)
    items = list(db.scalars(statement))
    return ChatSessionList(
        items=[serialize_chat_session(db, item) for item in items],
        total=int(db.scalar(count_statement) or 0),
    )


@router.post("/sessions", response_model=ChatSessionRead, status_code=201)
def create_session(request: ChatSessionCreate, db: Session = Depends(get_db)) -> ChatSessionRead:
    return serialize_chat_session(db, create_chat_session(db, request))


@router.post("/imports/chatgpt", response_model=ChatSessionRead, status_code=201)
def import_chatgpt_session(
    request: ChatGPTSharedImportRequest,
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_object_storage),
) -> ChatSessionRead:
    return serialize_chat_session(db, create_chatgpt_import_session(db, request, storage))


@router.get("/messages/{message_id}/media/{media_index}")
def message_media(
    message_id: str,
    media_index: int,
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_object_storage),
) -> StreamingResponse:
    message = db.get(ChatMessage, message_id)
    items = message.media_json if message is not None else None
    if (
        not isinstance(items, list)
        or media_index < 0
        or media_index >= len(items)
        or not isinstance(items[media_index], dict)
    ):
        raise DocumentError("CHAT_MEDIA_NOT_FOUND", "Imported chat image not found", 404)
    media = items[media_index]
    storage_key = media.get("storage_key")
    mime_type = media.get("mime_type")
    if not isinstance(storage_key, str) or mime_type not in {
        "image/avif",
        "image/gif",
        "image/jpeg",
        "image/png",
        "image/webp",
    }:
        raise DocumentError("CHAT_MEDIA_NOT_FOUND", "Imported chat image not found", 404)
    return StreamingResponse(
        storage.open(storage_key),
        media_type=mime_type,
        headers={
            "Cache-Control": "private, max-age=31536000, immutable",
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/sessions/{session_id}", response_model=ChatSessionRead)
def session(session_id: str, db: Session = Depends(get_db)) -> ChatSessionRead:
    return serialize_chat_session(db, get_chat_session(db, session_id))


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageRead])
def messages(session_id: str, db: Session = Depends(get_db)) -> list[ChatMessageRead]:
    return [serialize_chat_message(item) for item in list_chat_messages(db, session_id)]


@router.post("/sessions/{session_id}/messages", response_model=ChatTurnRead)
def create_message(
    session_id: str,
    request: ChatTurnRequest,
    db: Session = Depends(get_db),
) -> ChatTurnRead:
    item = get_chat_session(db, session_id)
    if item.credential_source == "personal":
        if request.personal_api_key is None:
            raise DocumentError("CHAT_PERSONAL_KEY_REQUIRED", "Personal API key required", 422)
        runtime = graph_chat_provider(
            item.provider_name, api_key=request.personal_api_key, model=item.model_name
        )
        return run_chat_turn(db, item, request.content, runtime=runtime)
    if request.personal_api_key is not None:
        raise DocumentError("CHAT_CREDENTIAL_MISMATCH", "Create a personal API chat first", 422)
    return run_chat_turn(db, item, request.content)


@router.post("/sessions/{session_id}/summarize", response_model=ChatSessionRead)
def summarize(
    session_id: str,
    request: ChatSummaryRequest,
    db: Session = Depends(get_db),
) -> ChatSessionRead:
    item = summarize_chat_session(db, get_chat_session(db, session_id), request)
    return serialize_chat_session(db, item)


@router.post("/sessions/{session_id}/close", response_model=ChatSessionRead)
def close(session_id: str, db: Session = Depends(get_db)) -> ChatSessionRead:
    return serialize_chat_session(db, close_chat_session(db, get_chat_session(db, session_id)))
