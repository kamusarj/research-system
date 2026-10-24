import logging
import re
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import settings
from app.core.observability import RATE_LIMITED

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RatePolicy:
    bucket: str
    limit_setting: str


RATE_POLICIES: tuple[tuple[str, re.Pattern[str], RatePolicy], ...] = (
    (
        "POST",
        re.compile(r"^/api/v1/auth/login/?$"),
        RatePolicy("auth-login", "auth_login_attempts_per_window"),
    ),
    (
        "POST",
        re.compile(r"^/api/v1/documents/?$"),
        RatePolicy("document-upload", "rate_limit_uploads_per_window"),
    ),
    (
        "POST",
        re.compile(r"^/api/v1/intake/receipts/?$"),
        RatePolicy("intake-receipt", "rate_limit_uploads_per_window"),
    ),
    (
        "POST",
        re.compile(r"^/api/v1/intake/receipts/[^/]+/documents/?$"),
        RatePolicy("intake-document-upload", "rate_limit_uploads_per_window"),
    ),
    (
        "POST",
        re.compile(r"^/api/v1/documents/[^/]+/(?:analyze|retry)$"),
        RatePolicy("document-analysis", "rate_limit_analysis_per_window"),
    ),
    (
        "POST",
        re.compile(r"^/api/v1/documents/edit-in-place/?$"),
        RatePolicy("document-instant-edit", "rate_limit_chat_per_window"),
    ),
    (
        "POST",
        re.compile(r"^/api/v1/documents/latex/compile/?$"),
        RatePolicy("latex-compile", "rate_limit_analysis_per_window"),
    ),
    (
        "POST",
        re.compile(r"^/api/v1/chat/sessions/[^/]+/messages$"),
        RatePolicy("graph-chat", "rate_limit_chat_per_window"),
    ),
    (
        "POST",
        re.compile(r"^/api/v1/chat/connections/(?:models|verify)/?$"),
        RatePolicy("chat-connection", "rate_limit_chat_per_window"),
    ),
    (
        "POST",
        re.compile(r"^/api/v1/chat/imports/chatgpt/?$"),
        RatePolicy("chat-import", "rate_limit_chat_per_window"),
    ),
    (
        "POST",
        re.compile(r"^/api/v1/graph/change-sets/[^/]+/apply$"),
        RatePolicy("graph-apply", "rate_limit_apply_per_window"),
    ),
    # Các lệnh dưới đây gọi nhà cung cấp AI/embedding có tính phí.
    (
        "POST",
        re.compile(r"^/api/v1/ingestion/links(?:/[^/]+/retry)?/?$"),
        RatePolicy("link-intake", "rate_limit_intake_per_window"),
    ),
    (
        "POST",
        re.compile(r"^/api/v1/documents/brainstorm/?$"),
        RatePolicy("document-brainstorm", "rate_limit_chat_per_window"),
    ),
    (
        "POST",
        re.compile(r"^/api/v1/documents/[^/]+/ai-edits/?$"),
        RatePolicy("document-ai-edit", "rate_limit_chat_per_window"),
    ),
    (
        "POST",
        re.compile(r"^/api/v1/documents/[^/]+/(?:graph/research|rag/rebuild)/?$"),
        RatePolicy("document-ai-analysis", "rate_limit_analysis_per_window"),
    ),
    (
        "POST",
        re.compile(r"^/api/v1/collector/sources/[^/]+/run/?$"),
        RatePolicy("collector-run", "rate_limit_analysis_per_window"),
    ),
    (
        "POST",
        re.compile(r"^/api/v1/(?:research-runs|gaps/[^/]+/research-run)/?$"),
        RatePolicy("research-run", "rate_limit_research_runs_per_window"),
    ),
    (
        "POST",
        re.compile(r"^/api/v1/ai/(?:summarize|extract-concepts|suggest-relations|enrich/[^/]+)$"),
        RatePolicy("ai-enrichment", "rate_limit_analysis_per_window"),
    ),
    (
        "POST",
        re.compile(r"^/api/v1/search/(?:semantic|hybrid)/?$"),
        RatePolicy("semantic-search", "rate_limit_chat_per_window"),
    ),
)


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def consume(
        self, bucket: str, identity: str, limit: int, window_seconds: int
    ) -> tuple[bool, int, int]:
        now = time.monotonic()
        cutoff = now - window_seconds
        key = (bucket, identity)
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, int(window_seconds - (now - events[0]) + 0.999))
                return False, 0, retry_after
            events.append(now)
            return True, max(0, limit - len(events)), 0

    def recent(self, bucket: str, identity: str, window_seconds: int) -> int:
        cutoff = time.monotonic() - window_seconds
        with self._lock:
            events = self._events.get((bucket, identity))
            if not events:
                return 0
            while events and events[0] <= cutoff:
                events.popleft()
            return len(events)

    def record(self, bucket: str, identity: str) -> None:
        with self._lock:
            self._events[(bucket, identity)].append(time.monotonic())

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


rate_limiter = SlidingWindowLimiter()


def _rate_policy(request: Request) -> RatePolicy | None:
    for method, pattern, policy in RATE_POLICIES:
        if request.method == method and pattern.fullmatch(request.url.path):
            return policy
    return None


def _rate_identity(request: Request) -> str:
    """Giới hạn theo người dùng đã đăng nhập; chỉ yêu cầu ẩn danh (đăng nhập) mới theo IP.

    Mọi yêu cầu trình duyệt đi qua proxy Next.js nên IP kết nối là của container frontend; nếu
    tính theo IP thì cả nhóm dùng chung một hạn mức. IP thật chỉ có khi uvicorn tin cậy
    X-Forwarded-For (FORWARDED_ALLOW_IPS trong bản triển khai nhóm).
    """

    principal = getattr(request.state, "principal", None)
    if principal is not None and principal.id != "local-user":
        return f"user:{principal.id}"
    return f"ip:{request.client.host if request.client else 'local'}"


def _feature_error(request: Request) -> str | None:
    path = request.url.path
    if not settings.graph_v2_enabled and (
        path.startswith("/api/v1/ontology")
        or path.startswith("/api/v1/documents")
        or path.startswith("/api/v1/chat")
        or path.startswith("/api/v1/graph/change-sets")
        or (path == "/api/v1/graph" and request.query_params.get("view") == "hierarchy")
    ):
        return "Tính năng Đồ thị tri thức v2 đang tắt"
    if not settings.graph_v2_documents_enabled and (
        path.startswith("/api/v1/documents")
        or re.fullmatch(r"/api/v1/intake/receipts/[^/]+/documents/?", path)
    ):
        return "Không gian tài liệu của Đồ thị tri thức đang tắt"
    if not settings.graph_v2_chat_enabled and path.startswith("/api/v1/chat"):
        return "Tính năng trò chuyện với Đồ thị tri thức đang tắt"
    return None


class RuntimeControlsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        feature_error = _feature_error(request)
        if feature_error:
            return JSONResponse(
                status_code=503,
                content={"error": {"code": "FEATURE_DISABLED", "message": feature_error}},
            )

        policy = _rate_policy(request) if settings.rate_limit_enabled else None
        rate_headers: dict[str, str] = {}
        if policy is not None:
            limit = max(1, int(getattr(settings, policy.limit_setting)))
            window = max(1, settings.rate_limit_window_seconds)
            identity = _rate_identity(request)
            allowed, remaining, retry_after = rate_limiter.consume(
                policy.bucket, identity, limit, window
            )
            rate_headers = {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Window": str(window),
            }
            if not allowed:
                RATE_LIMITED.labels(policy.bucket).inc()
                rate_headers["Retry-After"] = str(retry_after)
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMITED",
                            "message": "Thao tác này đã chạm giới hạn tần suất cục bộ",
                        }
                    },
                    headers=rate_headers,
                )

        started = time.monotonic()
        response = await call_next(request)
        if request.url.path.startswith("/api/v1/chat/connections/"):
            response.headers["Cache-Control"] = "no-store"
        elapsed_ms = round((time.monotonic() - started) * 1000, 2)
        response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
        response.headers["Server-Timing"] = f"app;dur={elapsed_ms}"
        for name, value in rate_headers.items():
            response.headers[name] = value
        if elapsed_ms >= settings.api_slow_request_ms:
            logger.warning(
                "Slow API request",
                extra={
                    "method": request.method,
                    "route": getattr(request.scope.get("route"), "path", "unmatched"),
                    "duration_ms": elapsed_ms,
                    "action": "http.request.slow",
                },
            )
        return response
