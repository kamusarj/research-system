from urllib.parse import urlparse

from app.schemas.source import SourceType
from app.services.sources.article import ArticleSourceAdapter
from app.services.sources.base import SourceAdapter, normalize_url
from app.services.sources.facebook_reel import FacebookReelSourceAdapter
from app.services.sources.github import GitHubSourceAdapter
from app.services.sources.pdf import PDFSourceAdapter


def detect_source_type(url: str) -> SourceType:
    parsed = urlparse(url)
    host = (parsed.hostname or "").casefold().removeprefix("www.")
    path = parsed.path.casefold()
    if host == "github.com" and len([part for part in parsed.path.split("/") if part]) >= 2:
        return "github"
    if host in {"facebook.com", "m.facebook.com", "fb.watch"} and (
        "/reel/" in f"{path}/" or "/reels/" in f"{path}/" or host == "fb.watch"
    ):
        return "facebook_reel"
    if path.endswith(".pdf"):
        return "pdf"
    return "article"


def adapter_for_url(url: str) -> SourceAdapter:
    adapters: dict[SourceType, SourceAdapter] = {
        "github": GitHubSourceAdapter(),
        "article": ArticleSourceAdapter(),
        "facebook_reel": FacebookReelSourceAdapter(),
        "pdf": PDFSourceAdapter(),
    }
    return adapters[detect_source_type(url)]


__all__ = ["adapter_for_url", "detect_source_type", "normalize_url"]
