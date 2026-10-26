"""Người dùng tự kết nối gói ChatGPT của mình (Sign in with ChatGPT) để dùng quota riêng."""

from collections.abc import Callable
from typing import TypeVar

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.identity import current_actor_id
from app.db import get_db
from app.models import AIPlanConnection
from app.schemas.ai_connections import (
    ChatGPTPlanComplete,
    ChatGPTPlanDisconnect,
    ChatGPTPlanDisconnectResult,
    ChatGPTPlanPreferences,
    ChatGPTPlanStart,
    ChatGPTPlanStatus,
)
from app.services import chatgpt_plan
from app.services.credentials_vault import VaultUnavailable

router = APIRouter(prefix="/ai-connections", tags=["ai-connections"])
T = TypeVar("T")


def _vault(action: Callable[[], T]) -> T:
    try:
        return action()
    except VaultUnavailable as exc:
        raise chatgpt_plan.ChatGPTPlanError(
            "CHATGPT_PLAN_VAULT_UNAVAILABLE", "Encryption key is not configured", 503
        ) from exc


def _status(connection: AIPlanConnection | None) -> ChatGPTPlanStatus:
    base = {
        "enabled": chatgpt_plan.enabled(),
        "mode": "local" if settings.chatgpt_plan_local_mode else "partner",
        "usage_url": chatgpt_plan.USAGE_URL,
    }
    if connection is None:
        return ChatGPTPlanStatus(status="not_connected", **base)
    return ChatGPTPlanStatus(
        status=connection.status,
        email=connection.email,
        model=connection.model,
        models=connection.models_json or [],
        use_by_default=connection.use_by_default,
        last_error_code=connection.last_error_code,
        connected_at=connection.connected_at,
        last_used_at=connection.last_used_at,
        **base,
    )


@router.get("/chatgpt", response_model=ChatGPTPlanStatus)
def chatgpt_status(db: Session = Depends(get_db)) -> ChatGPTPlanStatus:
    return _status(chatgpt_plan.get_connection(db, current_actor_id()))


@router.post("/chatgpt/start", response_model=ChatGPTPlanStart)
def chatgpt_start(db: Session = Depends(get_db)) -> ChatGPTPlanStart:
    url = _vault(lambda: chatgpt_plan.start_authorization(db, current_actor_id()))
    return ChatGPTPlanStart(authorize_url=url)


@router.post("/chatgpt/complete", response_model=ChatGPTPlanStatus)
def chatgpt_complete(
    data: ChatGPTPlanComplete, db: Session = Depends(get_db)
) -> ChatGPTPlanStatus:
    connection = _vault(
        lambda: chatgpt_plan.complete_authorization(
            db,
            current_actor_id(),
            state=data.state,
            code=data.code,
            callback_client_id=data.client_id,
            error=data.error,
        )
    )
    return _status(connection)


@router.post("/chatgpt/preferences", response_model=ChatGPTPlanStatus)
def chatgpt_preferences(
    data: ChatGPTPlanPreferences, db: Session = Depends(get_db)
) -> ChatGPTPlanStatus:
    connection = chatgpt_plan.set_preferences(
        db, current_actor_id(), model=data.model, use_by_default=data.use_by_default
    )
    return _status(connection)


@router.post("/chatgpt/disconnect", response_model=ChatGPTPlanDisconnectResult)
def chatgpt_disconnect(
    data: ChatGPTPlanDisconnect, db: Session = Depends(get_db)
) -> ChatGPTPlanDisconnectResult:
    actor = current_actor_id()
    revoked = _vault(lambda: chatgpt_plan.disconnect(db, actor, forget=data.forget))
    return ChatGPTPlanDisconnectResult(
        remote_revoked=revoked, connection=_status(chatgpt_plan.get_connection(db, actor))
    )
