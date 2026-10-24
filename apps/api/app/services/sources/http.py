import ipaddress
import re
import socket
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpcore
import httpx

from app.core.config import settings
from app.services.sources.errors import SourceError
from app.services.sources.politeness import host_rate_limiter, robots_policy

# Publishers commonly refuse unknown crawler agents outright. A current desktop browser
# identity is what a researcher opening the same link by hand would send.
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

# Content types that are readable text under a different name. Adapters ask for the family
# they can parse and these aliases resolve onto it.
CONTENT_TYPE_ALIASES = {
    "application/xhtml+xml": "text/html",
    "application/xhtml": "text/html",
    "text/markdown": "text/plain",
    "text/x-markdown": "text/plain",
    "text/csv": "text/plain",
    "application/json": "text/plain",
    "application/ld+json": "text/plain",
    "text/json": "text/plain",
    "application/x-pdf": "application/pdf",
    "application/acrobat": "application/pdf",
    "application/atom+xml": "application/atom+xml",
}

# Challenge pages answer with 403 while carrying a recognisable interstitial body or header.
BOT_CHALLENGE_HEADERS = ("cf-mitigated", "x-datadome", "x-akamai-bot")
BOT_CHALLENGE_MARKERS = (
    b"just a moment",
    b"cf-browser-verification",
    b"/cdn-cgi/challenge-platform",
    b"enable javascript and cookies to continue",
    b"attention required! | cloudflare",
    b"px-captcha",
    b"are you a robot",
)
CHALLENGE_SNIFF_BYTES = 65536

META_CHARSET_PATTERN = re.compile(
    rb"""<meta[^>]+charset\s*=\s*["']?\s*([a-zA-Z0-9_\-:.]+)""", re.IGNORECASE
)


@dataclass(slots=True)
class FetchedResource:
    final_url: str
    content_type: str
    content: bytes
    encoding: str
    status_code: int = 200
    headers: dict[str, str] | None = None

    @property
    def validators(self) -> dict[str, str]:
        """The values a later conditional request can use to ask "has this changed?"."""

        headers = self.headers or {}
        return {
            key: headers[key]
            for key in ("etag", "last-modified")
            if headers.get(key)
        }


class NotModified(Exception):
    """The server confirmed the cached copy is still current.

    Raised rather than returned so a caller that did not supply validators can never
    receive an empty body by accident.
    """

    def __init__(self, final_url: str) -> None:
        super().__init__("The source has not changed since it was last collected")
        self.final_url = final_url


def resolve_encoding(content: bytes, header_charset: str | None) -> str:
    """Pick the encoding a page is actually written in.

    The Content-Type charset is authoritative when the bytes decode cleanly under it.
    Many pages omit it or declare a default they do not honour, so a ``<meta charset>``
    declaration is consulted next and UTF-8 is the final assumption. Vietnamese content
    is the common casualty of guessing wrong.
    """

    candidates: list[str] = []
    if header_charset:
        candidates.append(header_charset)
    meta = META_CHARSET_PATTERN.search(content[:CHALLENGE_SNIFF_BYTES])
    if meta:
        candidates.append(meta.group(1).decode("ascii", errors="ignore"))
    candidates.append("utf-8")
    for candidate in candidates:
        normalized = candidate.strip().strip("\"'").casefold()
        if not normalized or normalized in {"none", "unknown"}:
            continue
        try:
            content.decode(normalized)
        except (LookupError, UnicodeDecodeError):
            continue
        return normalized
    return "utf-8"


def normalize_content_type(value: str | None) -> str:
    return (value or "").split(";", 1)[0].strip().casefold()


def header_charset(value: str | None) -> str | None:
    for part in (value or "").split(";")[1:]:
        key, _, candidate = part.partition("=")
        if key.strip().casefold() == "charset" and candidate.strip():
            return candidate.strip().strip("\"'")
    return None


def content_type_allowed(content_type: str, accepted: set[str]) -> bool:
    """Accept a declared type, a known alias of it, or any member of an accepted family."""

    if not content_type:
        # A missing Content-Type is common on static hosts; the adapter sniffs the body.
        return True
    if content_type in accepted:
        return True
    if CONTENT_TYPE_ALIASES.get(content_type) in accepted:
        return True
    family = content_type.split("/", 1)[0]
    return f"{family}/*" in accepted


def conditional_headers(validators: dict[str, str] | None) -> dict[str, str]:
    """Ask the server whether a previously collected copy is still current."""

    if not validators or not settings.intake_conditional_get:
        return {}
    headers: dict[str, str] = {}
    if validators.get("etag"):
        headers["If-None-Match"] = validators["etag"]
    if validators.get("last-modified"):
        headers["If-Modified-Since"] = validators["last-modified"]
    return headers


def request_headers_for(url: str, accepted_content_types: set[str]) -> dict[str, str]:
    accept = ", ".join(
        sorted(value for value in accepted_content_types if not value.endswith("/*"))
    )
    headers = {
        "User-Agent": settings.intake_user_agent or DEFAULT_USER_AGENT,
        "Accept": f"{accept},*/*;q=0.1" if accept else "*/*",
        "Accept-Language": settings.intake_accept_language,
        "Accept-Encoding": "gzip, deflate",
        "Cache-Control": "no-cache",
    }
    host = (urlparse(url).hostname or "").casefold().removeprefix("www.")
    overrides = settings.intake_host_headers.get(host)
    if overrides:
        headers.update(overrides)
    return headers


def _is_global(address: str) -> bool:
    try:
        return ipaddress.ip_address(address).is_global
    except ValueError:
        return False


def validate_public_url(url: str) -> None:
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError as exc:
        raise SourceError("INVALID_URL", "The URL is malformed") from exc
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise SourceError("INVALID_URL", "Only public HTTP(S) URLs are supported")
    if parsed.username or parsed.password:
        raise SourceError("INVALID_URL", "URLs containing credentials are not supported")
    try:
        addresses = socket.getaddrinfo(
            parsed.hostname,
            port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise SourceError("INVALID_URL", "The URL host could not be resolved") from exc
    for address in addresses:
        if not _is_global(address[4][0]):
            raise SourceError("INVALID_URL", "Private or local network URLs are not allowed")


class PinnedPublicBackend(httpcore.SyncBackend):
    """Kết nối TCP tới đúng địa chỉ công khai vừa kiểm tra, không để httpx phân giải lại.

    Kiểm tra địa chỉ rồi để thư viện tự phân giải lần nữa khi kết nối tạo khe hở DNS rebinding:
    bản ghi đổi sang 127.0.0.1/mạng nội bộ giữa hai lần tra. Ở đây tên miền chỉ được phân giải
    một lần, mọi địa chỉ phải là công khai và socket nối thẳng tới địa chỉ đó. TLS vẫn dùng tên
    miền gốc cho SNI và xác minh chứng chỉ.
    """

    def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        try:
            infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise SourceError("INVALID_URL", "The URL host could not be resolved") from exc
        addresses = list(dict.fromkeys(info[4][0] for info in infos))
        if not addresses or not all(_is_global(address) for address in addresses):
            raise SourceError("INVALID_URL", "Private or local network URLs are not allowed")
        last_error: Exception | None = None
        for address in addresses:
            try:
                return super().connect_tcp(
                    address, port, timeout, local_address, socket_options
                )
            except httpcore.ConnectError as exc:
                last_error = exc
        raise last_error or httpcore.ConnectError("No address could be connected")


def public_transport() -> httpx.HTTPTransport:
    transport = httpx.HTTPTransport()
    # httpx không mở tham số chọn network backend; thay backend của pool kết nối.
    transport._pool._network_backend = PinnedPublicBackend()
    return transport


def assert_peer_is_public(response: httpx.Response) -> None:
    """Confirm the connection actually landed on a public address.

    ``validate_public_url`` resolves the host itself, and httpx resolves it again when it
    connects. A record that changes between those two lookups would otherwise reach a
    private address, so the peer the socket really talks to is checked as well.
    """

    stream = response.extensions.get("network_stream")
    if stream is None:
        return
    peer = stream.get_extra_info("server_addr")
    if not peer:
        return
    address = peer[0] if isinstance(peer, tuple) else peer
    if not _is_global(str(address)):
        raise SourceError("INVALID_URL", "Private or local network URLs are not allowed")


def _body_is_challenge_page(body: bytes) -> bool:
    """Detect an interstitial served in place of the content, at any status code."""

    sniffed = body[:CHALLENGE_SNIFF_BYTES].lower()
    return any(marker in sniffed for marker in BOT_CHALLENGE_MARKERS)


def _refusal_is_bot_protection(response: httpx.Response, body: bytes) -> bool:
    """Distinguish a bot challenge from a plain authorization refusal.

    A great deal of the healthy web sits behind Cloudflare, so its presence only carries
    meaning once the request has already been refused.
    """

    if any(header in response.headers for header in BOT_CHALLENGE_HEADERS):
        return True
    if "cloudflare" in response.headers.get("server", "").casefold():
        return True
    return _body_is_challenge_page(body)


def _status_error(response: httpx.Response, body: bytes) -> SourceError:
    status = response.status_code
    if status == 404 or status == 410:
        return SourceError("SOURCE_NOT_FOUND", "The source was not found", status_code=status)
    if status == 401:
        return SourceError(
            "AUTH_REQUIRED", "The source requires authentication", status_code=status
        )
    if status == 402:
        return SourceError("PAYWALL", "The source is behind a paywall", status_code=status)
    if status == 403:
        if _refusal_is_bot_protection(response, body):
            return SourceError(
                "BOT_PROTECTED",
                "The source returned an automated-traffic challenge instead of content",
                status_code=status,
            )
        return SourceError("ACCESS_DENIED", "Access to the source was denied", status_code=status)
    if status == 429:
        return SourceError(
            "RATE_LIMITED",
            "The source rate limit was reached; retry later",
            retryable=True,
            status_code=status,
        )
    return SourceError(
        "FETCH_FAILED",
        f"The source returned HTTP {status}",
        # Server-side and congestion failures are rescheduled by the worker, which backs
        # off between attempts instead of holding this thread open.
        retryable=status in {408, 425} or status >= 500,
        status_code=status,
    )


def fetch_public(
    url: str,
    accepted_content_types: set[str],
    *,
    headers: dict[str, str] | None = None,
    max_bytes: int | None = None,
    validators: dict[str, str] | None = None,
) -> FetchedResource:
    """Fetch a bounded public resource with safe redirects and transient transport retry.

    Only transport faults (timeouts, refused connections) are retried here. Responses the
    server chose to send — 429, 5xx — are surfaced as retryable errors so the worker
    reschedules them with its own backoff, rather than multiplying attempts in both layers.
    """

    content_limit = max_bytes or settings.intake_max_content_bytes
    # httpx chỉ giới hạn thời gian chờ từng lần đọc; một máy chủ nhỏ giọt từng byte sẽ giữ worker
    # vô hạn. Hạn tổng theo thời gian thực bao cả chuyển hướng và các lần thử lại.
    deadline = time.monotonic() + settings.intake_request_timeout_seconds * (
        settings.intake_request_retries + 2
    )

    def check_deadline() -> None:
        if time.monotonic() > deadline:
            raise SourceError(
                "FETCH_TIMEOUT",
                "The source did not finish responding before the deadline",
                retryable=True,
            )

    # Kiểm tra địa chỉ trước cả robots.txt để không gửi yêu cầu nào tới máy nội bộ.
    validate_public_url(url)
    request_headers = {
        **request_headers_for(url, accepted_content_types),
        **conditional_headers(validators),
        **(headers or {}),
    }
    if not robots_policy().allows(url):
        raise SourceError(
            "ACCESS_DENIED",
            "The site's robots.txt asks automated readers not to fetch this address",
            details={"reason": "robots.txt"},
        )
    current_url = url
    redirects = 0
    attempt = 0
    while True:
        check_deadline()
        validate_public_url(current_url)
        # Space out requests to one host so a queue of links from one domain does not
        # arrive as fast as the worker can issue them.
        host_rate_limiter().wait(current_url)
        try:
            with httpx.Client(
                follow_redirects=False,
                timeout=httpx.Timeout(settings.intake_request_timeout_seconds),
                transport=public_transport(),
            ) as client:
                with client.stream("GET", current_url, headers=request_headers) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise SourceError("FETCH_FAILED", "Redirect response has no location")
                        redirects += 1
                        if redirects > settings.intake_max_redirects:
                            raise SourceError(
                                "FETCH_FAILED", "The source redirected too many times"
                            )
                        current_url = urljoin(current_url, location)
                        continue
                    assert_peer_is_public(response)
                    if response.status_code == 304:
                        raise NotModified(str(response.url))
                    content_type = normalize_content_type(response.headers.get("content-type"))
                    content_length = response.headers.get("content-length")
                    if content_length and content_length.isdigit():
                        if int(content_length) > content_limit:
                            raise SourceError(
                                "CONTENT_TOO_LARGE",
                                f"Source exceeds the {content_limit} byte limit",
                                details={"declared_bytes": int(content_length)},
                            )
                    if response.status_code < 400 and not content_type_allowed(
                        content_type, accepted_content_types
                    ):
                        # Refuse before pulling the body: an archive or video answers the
                        # request just as willingly as an article would.
                        raise SourceError(
                            "UNSUPPORTED_CONTENT_TYPE",
                            f"Unsupported source content type: {content_type or 'unknown'}",
                            status_code=415,
                            details={"content_type": content_type or "unknown"},
                        )
                    chunks: list[bytes] = []
                    size = 0
                    for chunk in response.iter_bytes():
                        check_deadline()
                        size += len(chunk)
                        if size > content_limit:
                            raise SourceError(
                                "CONTENT_TOO_LARGE",
                                f"Source exceeds the configured {content_limit} byte limit",
                                details={"limit_bytes": content_limit},
                            )
                        chunks.append(chunk)
                    body = b"".join(chunks)
                    if response.status_code >= 400:
                        raise _status_error(response, body)
                    final_url = str(response.url)
                    validate_public_url(final_url)
                    if _body_is_challenge_page(body):
                        raise SourceError(
                            "BOT_PROTECTED",
                            "The source returned an automated-traffic challenge "
                            "instead of content",
                            status_code=response.status_code,
                        )
                    return FetchedResource(
                        final_url=final_url,
                        content_type=content_type,
                        content=body,
                        encoding=resolve_encoding(
                            body, header_charset(response.headers.get("content-type"))
                        ),
                        status_code=response.status_code,
                        headers={key.casefold(): value for key, value in response.headers.items()},
                    )
        except (SourceError, NotModified):
            raise
        except httpx.TimeoutException as exc:
            if attempt < settings.intake_request_retries:
                attempt += 1
                time.sleep(settings.intake_request_backoff_seconds * (2 ** (attempt - 1)))
                continue
            raise SourceError(
                "FETCH_TIMEOUT",
                "The source did not respond before the timeout",
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            if attempt < settings.intake_request_retries:
                attempt += 1
                time.sleep(settings.intake_request_backoff_seconds * (2 ** (attempt - 1)))
                continue
            raise SourceError(
                "FETCH_FAILED",
                "The source could not be reached",
                retryable=True,
            ) from exc
