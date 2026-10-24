from __future__ import annotations

import contextvars
from dataclasses import dataclass

ROLE_LEVELS = {"viewer": 10, "researcher": 20, "owner": 30}


@dataclass(frozen=True, slots=True)
class Principal:
    id: str
    name: str
    email: str
    role: str
    session_id: str | None = None
    csrf_hash: str | None = None
    auth_kind: str = "session"
    scopes: tuple[str, ...] = ()
    source_namespace: str | None = None


principal_context: contextvars.ContextVar[Principal | None] = contextvars.ContextVar(
    "principal", default=None
)


def current_principal() -> Principal | None:
    return principal_context.get()


def current_actor_id() -> str:
    principal = current_principal()
    return principal.id if principal else "local-user"


def current_principal_may_publish() -> bool:
    """Tự duyệt xuất bản thẳng vào kho tri thức, nên chỉ chủ sở hữu (người duyệt) hoặc tài khoản
    dịch vụ tiếp nhận được cấp riêng (ví dụ cổng Discord) mới được yêu cầu."""
    principal = current_principal()
    if principal is None:
        return True
    return principal.auth_kind == "service" or has_role(principal.role, "owner")


def has_role(actual: str, required: str) -> bool:
    return ROLE_LEVELS.get(actual, 0) >= ROLE_LEVELS.get(required, 10_000)
