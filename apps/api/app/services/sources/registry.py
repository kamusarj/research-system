from urllib.parse import urlparse

from app.schemas.source import SourceType
from app.services.sources.article import ArticleSourceAdapter
from app.services.sources.base import SourceAdapter, normalize_url
from app.services.sources.facebook import FACEBOOK_HOSTS, FacebookSourceAdapter
from app.services.sources.github import GitHubSourceAdapter
from app.services.sources.paper import DOI_PATTERN, PUBLISHER_HOSTS, PaperSourceAdapter
from app.services.sources.pdf import PDFSourceAdapter


def detect_source_type(url: str, content_type: str | None = None) -> SourceType:
    parsed = urlparse(url)
    host = (parsed.hostname or "").casefold().removeprefix("www.")
    path = parsed.path.casefold()
    if content_type == "application/pdf":
        return "pdf"
    if host == "github.com" and len([part for part in parsed.path.split("/") if part]) >= 2:
        return "github"
    if host in FACEBOOK_HOSTS:
        return "facebook"
    publisher_hosts = {value.removeprefix("www.") for value in PUBLISHER_HOSTS}
    if host in publisher_hosts or DOI_PATTERN.search(url):
        return "paper"
    if path.endswith(".pdf"):
        return "pdf"
    return "article"


def adapter_for_url(url: str, content_type: str | None = None) -> SourceAdapter:
    adapters: dict[SourceType, SourceAdapter] = {
        "github": GitHubSourceAdapter(),
        "article": ArticleSourceAdapter(),
        "facebook": FacebookSourceAdapter(),
        "paper": PaperSourceAdapter(),
        "pdf": PDFSourceAdapter(),
    }
    return adapters[detect_source_type(url, content_type)]


__all__ = ["adapter_for_url", "detect_source_type", "normalize_url"]
