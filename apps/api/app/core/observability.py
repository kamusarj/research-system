from __future__ import annotations

import contextvars
import json
import logging
import os
import re
import sys
import time
import traceback
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
request_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)

LOG_FIELDS = (
    "action",
    "method",
    "route",
    "status_code",
    "duration_ms",
    "job_id",
    "job_type",
    "stage",
    "outcome",
    "error_code",
    "provider",
    "model",
    "operation",
    "validation_issue_count",
    "request_count",
    "blocked_count",
    "page_count",
    "output_chars",
    "decision",
    "graph_node_count",
    "graph_edge_count",
    "hierarchy_node_count",
    "hierarchy_edge_count",
    "search_document_count",
    "vector_chunk_count",
    "exception_type",
    "exception_location",
    "input_tokens",
    "output_tokens",
    "cached_input_tokens",
    "prompt_chars",
)

# Exception *messages* may carry credentials, document content or raw URLs, so they are
# never logged. Type names and code locations are owned by this repository and are safe.
TRACEBACK_FRAME_LIMIT = 5

HTTP_REQUESTS = Counter(
    "research_http_requests_total",
    "Completed Research System HTTP requests.",
    ("method", "route", "status_code"),
)
HTTP_REQUEST_DURATION = Histogram(
    "research_http_request_duration_seconds",
    "Research System HTTP request duration.",
    ("method", "route"),
)
RATE_LIMITED = Counter(
    "research_rate_limited_total",
    "Requests rejected by a local rate-limit bucket.",
    ("bucket",),
)
PROVIDER_CALLS = Counter(
    "research_provider_calls_total",
    "Completed AI provider calls.",
    ("provider", "model", "operation", "outcome"),
)
PROVIDER_CALL_DURATION = Histogram(
    "research_provider_call_duration_seconds",
    "AI provider call duration.",
    ("provider", "model", "operation"),
)
PROVIDER_TOKENS = Counter(
    "research_provider_tokens_total",
    "Provider-reported token usage.",
    ("provider", "model", "direction"),
)
WORKER_JOBS = Counter(
    "research_worker_jobs_total",
    "Completed background jobs in this process.",
    ("job_type", "outcome", "error_code"),
)
WORKER_JOB_DURATION = Histogram(
    "research_worker_job_duration_seconds",
    "Background job duration in this process.",
    ("job_type", "outcome"),
)
SOURCE_ENRICHMENTS = Counter(
    "research_source_enrichments_total",
    "Completed optional source-enrichment operations.",
    ("operation", "outcome", "error_code"),
)
SOURCE_ENRICHMENT_DURATION = Histogram(
    "research_source_enrichment_duration_seconds",
    "Optional source-enrichment operation duration.",
    ("operation", "outcome"),
)


def exception_fields(exc: BaseException) -> dict[str, str]:
    """Describe a failure by type and code location without exposing its message."""

    frames = traceback.extract_tb(exc.__traceback__)[-TRACEBACK_FRAME_LIMIT:]
    location = " < ".join(
        f"{os.path.basename(frame.filename)}:{frame.lineno}:{frame.name}"
        for frame in reversed(frames)
    )
    fields = {"exception_type": type(exc).__qualname__}
    if location:
        fields["exception_location"] = location
    return fields


def safe_request_id(candidate: str | None) -> str:
    if candidate and REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return str(uuid.uuid4())


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if not isinstance(path, str) or not path:
        return "unmatched"
    if request.url.path.startswith("/api/v1/") and not path.startswith("/api/v1/"):
        return f"/api/v1{path}"
    return path


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_context.get()
        if request_id:
            payload["request_id"] = request_id
        for field in LOG_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    root.setLevel(level)
    formatter = JsonLogFormatter()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        root.addHandler(handler)
    else:
        for handler in root.handlers:
            handler.setFormatter(formatter)
    for noisy_logger in ("httpx", "httpcore"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
    # The driver notification logger includes raw Cypher in its message. Application-owned
    # projection logs already emit bounded outcomes/counts, so suppress all driver messages.
    logging.getLogger("neo4j").setLevel(logging.CRITICAL + 1)
    logging.getLogger("uvicorn.access").disabled = True


def observe_provider_call(
    *, provider: str, model: str, operation: str, duration_seconds: float, outcome: str
) -> None:
    PROVIDER_CALLS.labels(provider, model, operation, outcome).inc()
    PROVIDER_CALL_DURATION.labels(provider, model, operation).observe(duration_seconds)


@contextmanager
def provider_observation(
    *, provider: str, model: str, operation: str
) -> Iterator[dict[str, Any]]:
    # Nhập muộn để module quan sát không phụ thuộc tầng dịch vụ khi khởi động.
    from app.services.ai_usage import USAGE_FIELDS, collect_usage, record_call

    started = time.monotonic()
    outcome = "success"
    with collect_usage() as usage:
        try:
            yield usage
        except Exception:
            outcome = "error"
            raise
        finally:
            duration_seconds = time.monotonic() - started
            observe_provider_call(
                provider=provider,
                model=model,
                operation=operation,
                duration_seconds=duration_seconds,
                outcome=outcome,
            )
            observe_provider_tokens(provider=provider, model=model, usage=usage)
            token_fields = {key: usage[key] for key in USAGE_FIELDS if key in usage}
            logging.getLogger("research.provider").info(
                "AI provider call completed",
                extra={
                    "action": "provider.call.completed",
                    "provider": provider,
                    "model": model,
                    "operation": operation,
                    "outcome": outcome,
                    "duration_ms": round(duration_seconds * 1000, 2),
                    **token_fields,
                },
            )
            record_call(
                {
                    "operation": operation[:80],
                    "provider": provider[:50],
                    "model": model[:120],
                    "outcome": outcome,
                    "latency_ms": round(duration_seconds * 1000),
                    "cache_hit": bool(usage.get("cache_hit")),
                    **{key: usage.get(key) for key in USAGE_FIELDS},
                }
            )


def observe_provider_tokens(*, provider: str, model: str, usage: dict[str, Any]) -> None:
    for key, direction in (("input_tokens", "input"), ("output_tokens", "output")):
        value = usage.get(key)
        if isinstance(value, int) and value >= 0:
            PROVIDER_TOKENS.labels(provider, model, direction).inc(value)


def observe_worker_job(
    *, job_type: str, outcome: str, error_code: str | None, duration_seconds: float
) -> None:
    bounded_error = error_code or "none"
    WORKER_JOBS.labels(job_type, outcome, bounded_error).inc()
    WORKER_JOB_DURATION.labels(job_type, outcome).observe(duration_seconds)


def observe_source_enrichment(
    *, operation: str, outcome: str, error_code: str | None, duration_seconds: float
) -> None:
    SOURCE_ENRICHMENTS.labels(operation, outcome, error_code or "none").inc()
    SOURCE_ENRICHMENT_DURATION.labels(operation, outcome).observe(duration_seconds)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = safe_request_id(request.headers.get("X-Request-ID"))
        token = request_id_context.set(request_id)
        started = time.monotonic()
        status_code = 500
        try:
            try:
                response = await call_next(request)
            except Exception as exc:
                logging.getLogger("research.http").error(
                    "Unhandled API error",
                    extra={
                        "action": "http.request.failed",
                        "error_code": "INTERNAL_ERROR",
                        "exception_type": type(exc).__name__,
                    },
                )
                response = Response(
                    content=json.dumps(
                        {
                            "error": {
                                "code": "INTERNAL_ERROR",
                                "message": "Máy chủ chưa thể hoàn tất yêu cầu này",
                            }
                        },
                        separators=(",", ":"),
                    ),
                    status_code=500,
                    media_type="application/json",
                )
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration_seconds = time.monotonic() - started
            route = _route_template(request)
            HTTP_REQUESTS.labels(request.method, route, str(status_code)).inc()
            HTTP_REQUEST_DURATION.labels(request.method, route).observe(duration_seconds)
            logging.getLogger("research.http").info(
                "HTTP request completed",
                extra={
                    "action": "http.request.completed",
                    "method": request.method,
                    "route": route,
                    "status_code": status_code,
                    "duration_ms": round(duration_seconds * 1000, 2),
                },
            )
            request_id_context.reset(token)
