import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

from app.core.config import settings


@dataclass
class FetchedResource:
    final_url: str
    content_type: str
    content: bytes
    encoding: str


def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(422, "Only public HTTP(S) URLs are supported")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise HTTPException(422, "URL host cannot be resolved") from exc
    for address in addresses:
        if not ipaddress.ip_address(address[4][0]).is_global:
            raise HTTPException(422, "Private or local network URLs are not allowed")


def fetch_public(url: str, accepted_content_types: set[str]) -> FetchedResource:
    validate_public_url(url)
    try:
        with httpx.Client(follow_redirects=True, timeout=30) as client:
            response = client.get(
                url,
                headers={"User-Agent": "ResearchSystemBot/1.0 (+local research intake)"},
            )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status in {401, 403}:
            raise HTTPException(status, "Source requires authentication or denied access") from exc
        raise
    validate_public_url(str(response.url))
    content_type = response.headers.get("content-type", "").split(";", 1)[0].casefold()
    if content_type not in accepted_content_types:
        raise HTTPException(415, f"Unsupported source content type: {content_type or 'unknown'}")
    return FetchedResource(
        final_url=str(response.url),
        content_type=content_type,
        content=response.content[: settings.intake_max_content_bytes],
        encoding=response.encoding or "utf-8",
    )
