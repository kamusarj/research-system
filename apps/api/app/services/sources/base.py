import hashlib
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.schemas.source import NormalizedSource, SourceType

TRACKING_PARAMETERS = {
    "fbclid",
    "gclid",
    "dclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "spm",
}


@dataclass(slots=True)
class RawSource:
    requested_url: str
    final_url: str
    content_type: str
    content: bytes = b""
    encoding: str = "utf-8"
    status_code: int = 200
    headers: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


class SourceAdapter(Protocol):
    source_type: SourceType

    def can_handle(self, url: str) -> bool: ...

    def fetch(self, url: str) -> RawSource: ...

    def extract(self, source: RawSource) -> NormalizedSource: ...

    def collect(self, url: str) -> NormalizedSource: ...


def normalize_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    scheme = parsed.scheme.casefold()
    hostname = (parsed.hostname or "").casefold()
    if scheme not in {"http", "https"} or not hostname:
        return url.strip()
    port = parsed.port
    netloc = hostname
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{hostname}:{port}"
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.casefold() not in TRACKING_PARAMETERS and not key.casefold().startswith("utm_")
    ]
    path = parsed.path or "/"
    while "//" in path:
        path = path.replace("//", "/")
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((scheme, netloc, path, urlencode(sorted(query)), ""))


def stable_source_id(source_type: SourceType, canonical_url: str) -> str:
    digest = hashlib.sha256(canonical_url.encode()).hexdigest()[:24]
    return f"{source_type}:{digest}"
