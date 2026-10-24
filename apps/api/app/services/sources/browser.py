from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from urllib.parse import urlencode

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Route, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.core.config import settings
from app.core.observability import observe_source_enrichment
from app.services.sources.base import RawSource
from app.services.sources.errors import SourceError
from app.services.sources.http import validate_public_url

logger = logging.getLogger("research-worker.browser")
BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}


@dataclass(slots=True)
class BrowserRenderResult:
    raw: RawSource | None = None
    limitation_code: str | None = None
    limitation_message: str | None = None
    request_count: int = 0
    blocked_count: int = 0


def _finish(
    result: BrowserRenderResult, started: float, *, outcome: str | None = None
) -> BrowserRenderResult:
    outcome = outcome or ("success" if result.raw else "error")
    duration_seconds = time.monotonic() - started
    observe_source_enrichment(
        operation="article-browser-render",
        outcome=outcome,
        error_code=result.limitation_code,
        duration_seconds=duration_seconds,
    )
    logger.info(
        "Browser enrichment completed",
        extra={
            "action": "source.enrichment.completed",
            "operation": "article-browser-render",
            "outcome": outcome,
            "error_code": result.limitation_code,
            "duration_ms": round(duration_seconds * 1000, 2),
            "request_count": result.request_count,
            "blocked_count": result.blocked_count,
            "output_chars": len(result.raw.content) if result.raw else 0,
        },
    )
    return result


def _connection_url() -> str | None:
    if settings.browserless_token is None:
        return None
    token = settings.browserless_token.get_secret_value().strip()
    if not token:
        return None
    base = settings.browserless_ws_url.rstrip("/")
    return f"{base}/chromium/playwright?{urlencode({'token': token})}"


def _route_public_request(route: Route, counters: dict[str, int]) -> None:
    counters["request_count"] += 1
    request = route.request
    if request.resource_type in BLOCKED_RESOURCE_TYPES:
        counters["blocked_count"] += 1
        route.abort()
        return
    try:
        validate_public_url(request.url)
    except SourceError:
        counters["blocked_count"] += 1
        route.abort()
        return
    route.continue_()


def render_public_article(url: str) -> BrowserRenderResult:
    started = time.monotonic()
    if not settings.browser_render_enabled:
        return _finish(BrowserRenderResult(), started, outcome="disabled")
    endpoint = _connection_url()
    if endpoint is None:
        return _finish(
            BrowserRenderResult(
                limitation_code="BROWSER_RENDER_UNAVAILABLE",
                limitation_message=(
                    "Browser rendering is enabled but its credential is unavailable."
                ),
            ),
            started,
            outcome="unavailable",
        )

    counters = {"request_count": 0, "blocked_count": 0}
    try:
        validate_public_url(url)
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect(
                endpoint,
                timeout=max(
                    1, min(int(settings.browser_render_timeout_seconds * 1000), 60_000)
                ),
            )
            try:
                context = browser.new_context(service_workers="block", accept_downloads=False)
                try:
                    context.route(
                        "**/*", lambda route: _route_public_request(route, counters)
                    )
                    page = context.new_page()
                    page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=max(
                            1,
                            min(int(settings.browser_render_timeout_seconds * 1000), 60_000),
                        ),
                    )
                    wait_ms = min(max(0, settings.browser_render_wait_ms), 5_000)
                    if wait_ms:
                        page.wait_for_timeout(wait_ms)
                    final_url = page.url
                    validate_public_url(final_url)
                    content = page.content().encode("utf-8")
                    content_limit = max(
                        1, min(settings.browser_render_max_bytes, 10_000_000)
                    )
                    if len(content) > content_limit:
                        return _finish(BrowserRenderResult(
                            limitation_code="BROWSER_RENDER_FAILED",
                            limitation_message=(
                                "Rendered article exceeds the configured size limit."
                            ),
                            **counters,
                        ), started)
                    return _finish(BrowserRenderResult(
                        raw=RawSource(
                            requested_url=url,
                            final_url=final_url,
                            content_type="text/html",
                            content=content,
                            encoding="utf-8",
                            metadata={"browser_rendered": True},
                        ),
                        **counters,
                    ), started)
                finally:
                    context.close()
            finally:
                browser.close()
    except PlaywrightTimeoutError:
        result = BrowserRenderResult(
            limitation_code="BROWSER_RENDER_FAILED",
            limitation_message=(
                "Việc dựng trang bằng trình duyệt đã vượt thời gian chờ được cấu hình."
            ),
            **counters,
        )
        return _finish(result, started, outcome="timeout")
    except SourceError:
        result = BrowserRenderResult(
            limitation_code="BROWSER_RENDER_FAILED",
            limitation_message="Đích trình duyệt không phải địa chỉ công khai được phép.",
            **counters,
        )
        return _finish(result, started, outcome="rejected_target")
    except (PlaywrightError, OSError):
        result = BrowserRenderResult(
            limitation_code="BROWSER_RENDER_FAILED",
            limitation_message="Không thể dựng bài viết công khai một cách an toàn.",
            **counters,
        )
    return _finish(result, started)
