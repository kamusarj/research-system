from __future__ import annotations

import hmac
import re

from fastapi import Request
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.identity import Principal, has_role, principal_context
from app.db import SessionLocal
from app.services.auth import hash_token, resolve_service_account, resolve_session

PUBLIC_PATHS = {
    "/api/v1/health",
    "/api/v1/auth/config",
    "/api/v1/auth/login",
}
VIEWER_POST_PATTERNS = (
    re.compile(r"^/api/v1/search/semantic/?$"),
    re.compile(r"^/api/v1/ontology/validate-placement/?$"),
    re.compile(r"^/api/v1/auth/logout/?$"),
    re.compile(r"^/api/v1/auth/me/password/?$"),
)
OWNER_PATTERNS = (
    re.compile(r"^/api/v1/auth/users(?:/[^/]+)?/?$"),
    re.compile(r"^/api/v1/auth/service-accounts(?:/[^/]+)?/?$"),
    re.compile(r"^/api/v1/research/[^/]+/(?:approve|reject|archive)/?$"),
    re.compile(r"^/api/v1/collector/review-queue/[^/]+/(?:approve|reject|edit-and-approve)/?$"),
    re.compile(r"^/api/v1/ingestion/links/[^/]+/(?:approve|reject)/?$"),
    re.compile(r"^/api/v1/ingestion/links/bulk-review/?$"),
    # Ngưỡng tự duyệt của nguồn RSS quyết định nội dung được xuất bản, nên chỉ chủ sở hữu cấu hình.
    re.compile(r"^/api/v1/collector/sources(?:/[^/]+)?/?$"),
    re.compile(r"^/api/v1/deep-research/[^/]+/approve/?$"),
    re.compile(r"^/api/v1/graph/rebuild/?$"),
    re.compile(r"^/api/v1/search/rebuild/?$"),
    re.compile(
        r"^/api/v1/graph/change-sets/[^/]+/"
        r"(?:mutations/[^/]+/decision|approve|reject|apply|compensate)/?$"
    ),
    re.compile(r"^/api/v1/ai/outputs/[^/]+/accept/?$"),
)
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
SERVICE_RECEIPT_READ = re.compile(r"^/api/v1/intake/receipts/[^/]+/?$")
SERVICE_RECEIPT_DOCUMENT = re.compile(r"^/api/v1/intake/receipts/[^/]+/documents/?$")


def required_role(method: str, path: str) -> str:
    if path.startswith(("/api/v1/auth/users", "/api/v1/auth/service-accounts")):
        return "owner"
    if method == "DELETE":
        return "owner"
    if method in SAFE_METHODS or any(pattern.fullmatch(path) for pattern in VIEWER_POST_PATTERNS):
        return "viewer"
    if any(pattern.fullmatch(path) for pattern in OWNER_PATTERNS):
        return "owner"
    return "researcher"


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    headers = {"WWW-Authenticate": "Cookie, Bearer"} if status_code == 401 else None
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
        headers=headers,
    )


def _local_principal() -> Principal:
    return Principal(
        id="local-user",
        name="Chủ sở hữu cục bộ",
        email="local@research.invalid",
        role="owner",
    )


def _resolve(session_factory, raw_token: str) -> Principal | None:
    with session_factory() as db:
        return resolve_session(db, raw_token)


def _resolve_bearer(session_factory, raw_token: str) -> Principal | None:
    with session_factory() as db:
        return resolve_service_account(db, raw_token)


def _service_scope_allowed(principal: Principal, method: str, path: str) -> bool:
    scopes = set(principal.scopes)
    if method == "POST" and path.rstrip("/") == "/api/v1/intake/receipts":
        return "intake:submit" in scopes
    if method == "POST" and SERVICE_RECEIPT_DOCUMENT.fullmatch(path):
        return "intake:submit" in scopes
    if method == "GET" and path.rstrip("/") == "/api/v1/intake/receipts":
        return "intake:read-own" in scopes
    if method == "GET" and SERVICE_RECEIPT_READ.fullmatch(path):
        return "intake:read-own" in scopes
    return False


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path
        if not path.startswith("/api/v1") or request.method == "OPTIONS":
            return await call_next(request)
        if path in PUBLIC_PATHS:
            return await call_next(request)

        session_factory = getattr(request.app.state, "auth_session_factory", SessionLocal)
        authorization = request.headers.get("Authorization", "")
        scheme, separator, bearer_token = authorization.partition(" ")
        if separator == " " and scheme.casefold() == "bearer":
            principal = await run_in_threadpool(
                _resolve_bearer, session_factory, bearer_token
            )
            if principal is None:
                return _error(
                    401,
                    "AUTH_REQUIRED",
                    "Thông tin xác thực đã hết hạn hoặc không hợp lệ",
                )
        elif not settings.auth_enabled:
            principal = _local_principal()
        else:
            raw_token = request.cookies.get(settings.auth_cookie_name)
            if not raw_token:
                return _error(401, "AUTH_REQUIRED", "Bạn cần đăng nhập để tiếp tục")
            principal = await run_in_threadpool(_resolve, session_factory, raw_token)
            if principal is None:
                return _error(401, "AUTH_REQUIRED", "Phiên đăng nhập đã hết hạn hoặc không hợp lệ")

        if principal.auth_kind == "service" and not _service_scope_allowed(
            principal, request.method, path
        ):
            return _error(
                403,
                "ACCESS_DENIED",
                "Phạm vi của tài khoản dịch vụ không cho phép thao tác này",
            )

        role = required_role(request.method, path)
        if not has_role(principal.role, role):
            return _error(403, "ACCESS_DENIED", "Bạn không có quyền thực hiện thao tác này")

        if (
            settings.auth_enabled
            and principal.auth_kind != "service"
            and request.method not in SAFE_METHODS
        ):
            csrf_cookie = request.cookies.get(settings.auth_csrf_cookie_name, "")
            csrf_header = request.headers.get("X-CSRF-Token", "")
            if (
                not csrf_cookie
                or not csrf_header
                or not hmac.compare_digest(csrf_cookie, csrf_header)
                or principal.csrf_hash is None
                or not hmac.compare_digest(hash_token(csrf_header), principal.csrf_hash)
            ):
                return _error(403, "CSRF_REQUIRED", "Cần mã CSRF hợp lệ để thực hiện thao tác này")

        request.state.principal = principal
        token = principal_context.set(principal)
        try:
            return await call_next(request)
        finally:
            principal_context.reset(token)
