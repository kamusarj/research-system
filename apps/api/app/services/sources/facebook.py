from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from app.schemas.source import NormalizedSource, SourceMedia
from app.services.sources.base import RawSource, normalize_url, stable_source_id
from app.services.sources.http import fetch_public

FACEBOOK_HOSTS = {"facebook.com", "m.facebook.com", "fb.watch"}


class FacebookMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.values: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "meta":
            return
        values = {key.casefold(): value for key, value in attrs}
        key = (values.get("property") or values.get("name") or "").casefold()
        content = values.get("content")
        if key and content:
            self.values[key] = content


def facebook_resource_kind(url: str) -> str:
    path = urlparse(url).path.casefold()
    if "/reel/" in f"{path}/" or "/reels/" in f"{path}/" or urlparse(url).hostname == "fb.watch":
        return "reel"
    if "/videos/" in f"{path}/":
        return "video"
    return "post"


class FacebookSourceAdapter:
    source_type = "facebook"

    def can_handle(self, url: str) -> bool:
        host = (urlparse(url).hostname or "").casefold().removeprefix("www.")
        return host in FACEBOOK_HOSTS

    def fetch(self, url: str) -> RawSource:
        resource = fetch_public(
            url,
            {"text/html"},
            headers={"Accept-Language": "en-US,en;q=0.8"},
        )
        return RawSource(
            requested_url=url,
            final_url=resource.final_url,
            content_type=resource.content_type,
            content=resource.content,
            encoding=resource.encoding,
            status_code=resource.status_code,
            headers=resource.headers or {},
        )

    def extract(self, source: RawSource) -> NormalizedSource:
        parser = FacebookMetadataParser()
        parser.feed(source.content.decode(source.encoding, errors="replace"))
        canonical = normalize_url(parser.values.get("og:url") or source.final_url)
        kind = facebook_resource_kind(canonical)
        title = parser.values.get("og:title") or f"Facebook {kind.title()}"
        description = parser.values.get("og:description") or ""
        video = parser.values.get("og:video:url") or parser.values.get("og:video")
        image = parser.values.get("og:image")
        media = []
        if video:
            media.append(SourceMedia(type="video", url=urljoin(source.final_url, video)))
        if image:
            media.append(SourceMedia(type="image", url=urljoin(source.final_url, image)))
        limitation = (
            "Public Open Graph metadata was collected, but Facebook did not provide a transcript."
            if kind in {"reel", "video"}
            else (
                "Only public Open Graph metadata was available; the full post may require "
                "login or permission."
            )
        )
        return NormalizedSource(
            id=stable_source_id(self.source_type, canonical),
            source_type=self.source_type,
            canonical_url=canonical,
            title=title,
            description=description,
            raw_text=description,
            summary=description,
            media=media,
            metadata={
                "resource_kind": kind,
                "metadata_only": True,
                "login_bypass_attempted": False,
            },
            collection_status="PARTIAL",
            limitation_code="TRANSCRIPT_UNAVAILABLE"
            if kind in {"reel", "video"}
            else "METADATA_ONLY",
            limitation_message=limitation,
        )

    def collect(self, url: str) -> NormalizedSource:
        return self.extract(self.fetch(url))
