import hashlib
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.schemas.source import NormalizedSource, SourceType

TRACKING_PARAMETERS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


class SourceAdapter(Protocol):
    source_type: SourceType

    def collect(self, url: str) -> NormalizedSource: ...


def normalize_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    scheme = parsed.scheme.casefold()
    hostname = (parsed.hostname or "").casefold()
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
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((scheme, netloc, path, urlencode(sorted(query)), ""))


def stable_source_id(source_type: SourceType, canonical_url: str) -> str:
    digest = hashlib.sha256(canonical_url.encode()).hexdigest()[:24]
    return f"{source_type}:{digest}"
