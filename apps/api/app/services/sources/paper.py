import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlparse

import httpx

from app.core.config import settings
from app.schemas.source import NormalizedSource, SourceMedia
from app.services.sources.base import RawSource, normalize_url, stable_source_id
from app.services.sources.errors import SourceError
from app.services.sources.http import fetch_public

PUBLISHER_HOSTS = {
    "arxiv.org",
    "doi.org",
    "dx.doi.org",
    "semanticscholar.org",
    "ieeexplore.ieee.org",
    "dl.acm.org",
    "link.springer.com",
    "sciencedirect.com",
    "www.sciencedirect.com",
}
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
ARXIV_PATTERN = re.compile(
    r"(?:abs|pdf)/((?:[a-z-]+/)?\d{4}\.\d{4,5}|[a-z-]+/\d{7})(?:v\d+)?", re.I
)


class CitationParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, list[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "meta":
            return
        values = {key.casefold(): value for key, value in attrs}
        key = (values.get("name") or values.get("property") or "").casefold()
        content = values.get("content")
        if key and content:
            self.meta.setdefault(key, []).append(content)


def _datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    for candidate in (value, value.replace("Z", "+00:00")):
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue
    return None


def _api_json(url: str) -> dict[str, object]:
    try:
        response = httpx.get(
            url,
            headers={"User-Agent": "ResearchSystem/1.0 (mailto:local@example.invalid)"},
            timeout=settings.intake_request_timeout_seconds,
        )
    except httpx.TimeoutException as exc:
        raise SourceError(
            "FETCH_TIMEOUT", "Paper metadata service timed out", retryable=True
        ) from exc
    except httpx.RequestError as exc:
        raise SourceError(
            "FETCH_FAILED", "Paper metadata service could not be reached", retryable=True
        ) from exc
    if response.status_code == 404:
        raise SourceError("SOURCE_NOT_FOUND", "Paper metadata was not found")
    if response.status_code == 429:
        raise SourceError(
            "RATE_LIMITED", "Paper metadata service rate limit reached", retryable=True
        )
    if response.status_code >= 400:
        raise SourceError(
            "FETCH_FAILED",
            f"Paper metadata service returned HTTP {response.status_code}",
            retryable=response.status_code >= 500,
        )
    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise SourceError("EXTRACTION_FAILED", "Paper metadata response was invalid") from exc
    if not isinstance(payload, dict):
        raise SourceError("EXTRACTION_FAILED", "Paper metadata response was invalid")
    return payload


def _doi_csl_json(doi: str) -> dict[str, object]:
    resource = fetch_public(
        f"https://doi.org/{doi}",
        {"application/json", "application/vnd.citationstyles.csl+json"},
        headers={"Accept": "application/vnd.citationstyles.csl+json"},
    )
    try:
        payload = json.loads(resource.content)
    except json.JSONDecodeError as exc:
        raise SourceError("EXTRACTION_FAILED", "DOI metadata response was invalid") from exc
    if not isinstance(payload, dict):
        raise SourceError("EXTRACTION_FAILED", "DOI metadata response was invalid")
    return payload


class PaperSourceAdapter:
    source_type = "paper"

    def can_handle(self, url: str) -> bool:
        parsed = urlparse(url)
        host = (parsed.hostname or "").casefold().removeprefix("www.")
        return host in {value.removeprefix("www.") for value in PUBLISHER_HOSTS} or bool(
            DOI_PATTERN.search(url)
        )

    def fetch(self, url: str) -> RawSource:
        arxiv = ARXIV_PATTERN.search(url)
        if arxiv and "arxiv.org" in (urlparse(url).hostname or ""):
            arxiv_id = arxiv.group(1)
            try:
                response = httpx.get(
                    f"https://export.arxiv.org/api/query?id_list={quote(arxiv_id)}",
                    headers={"User-Agent": "ResearchSystem/1.0"},
                    timeout=settings.intake_request_timeout_seconds,
                )
                response.raise_for_status()
            except httpx.TimeoutException as exc:
                raise SourceError(
                    "FETCH_TIMEOUT", "arXiv metadata request timed out", retryable=True
                ) from exc
            except httpx.HTTPError as exc:
                raise SourceError(
                    "FETCH_FAILED", "arXiv metadata could not be fetched", retryable=True
                ) from exc
            return RawSource(
                requested_url=url,
                final_url=f"https://arxiv.org/abs/{arxiv_id}",
                content_type="application/atom+xml",
                content=response.content,
                metadata={"provider": "arxiv", "arxiv_id": arxiv_id},
            )

        doi = DOI_PATTERN.search(url)
        if doi:
            doi_value = doi.group(0).rstrip(".,);]")
            provider = "crossref"
            try:
                payload = _api_json(f"https://api.crossref.org/works/{quote(doi_value, safe='')}")
            except SourceError as exc:
                if exc.code != "SOURCE_NOT_FOUND":
                    raise
                payload = _doi_csl_json(doi_value)
                provider = "doi_csl"
            return RawSource(
                requested_url=url,
                final_url=f"https://doi.org/{doi_value}",
                content_type=(
                    "application/vnd.crossref+json"
                    if provider == "crossref"
                    else "application/vnd.citationstyles.csl+json"
                ),
                content=json.dumps(payload).encode(),
                metadata={"provider": provider, "doi": doi_value},
            )

        host = (urlparse(url).hostname or "").casefold()
        if "semanticscholar.org" in host:
            paper_id = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
            payload = _api_json(
                "https://api.semanticscholar.org/graph/v1/paper/"
                f"{quote(paper_id, safe='')}?fields=title,abstract,authors,year,publicationDate,"
                "externalIds,openAccessPdf,url"
            )
            return RawSource(
                requested_url=url,
                final_url=url,
                content_type="application/vnd.semanticscholar+json",
                content=json.dumps(payload).encode(),
                metadata={"provider": "semantic_scholar"},
            )

        resource = fetch_public(url, {"text/html"})
        return RawSource(
            requested_url=url,
            final_url=resource.final_url,
            content_type=resource.content_type,
            content=resource.content,
            encoding=resource.encoding,
            status_code=resource.status_code,
            headers=resource.headers or {},
            metadata={"provider": "publisher"},
        )

    def extract(self, source: RawSource) -> NormalizedSource:
        provider = source.metadata.get("provider")
        if provider == "arxiv":
            return self._extract_arxiv(source)
        if provider == "crossref":
            return self._extract_crossref(source)
        if provider == "doi_csl":
            return self._extract_doi_csl(source)
        if provider == "semantic_scholar":
            return self._extract_semantic_scholar(source)
        return self._extract_publisher(source)

    def _extract_arxiv(self, source: RawSource) -> NormalizedSource:
        try:
            root = ET.fromstring(source.content)
        except ET.ParseError as exc:
            raise SourceError("EXTRACTION_FAILED", "arXiv metadata could not be parsed") from exc
        namespace = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }
        entry = root.find("atom:entry", namespace)
        if entry is None:
            raise SourceError("SOURCE_NOT_FOUND", "arXiv paper was not found")
        arxiv_id = str(source.metadata.get("arxiv_id"))
        canonical = f"https://arxiv.org/abs/{arxiv_id}"
        title = " ".join((entry.findtext("atom:title", default="", namespaces=namespace)).split())
        abstract = " ".join(
            (entry.findtext("atom:summary", default="", namespaces=namespace)).split()
        )
        authors = [
            " ".join((author.findtext("atom:name", default="", namespaces=namespace)).split())
            for author in entry.findall("atom:author", namespace)
        ]
        doi = entry.findtext("arxiv:doi", default="", namespaces=namespace)
        published = entry.findtext("atom:published", default="", namespaces=namespace)
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        return NormalizedSource(
            id=stable_source_id(self.source_type, canonical),
            source_type=self.source_type,
            canonical_url=canonical,
            title=title or f"arXiv {arxiv_id}",
            authors=[author for author in authors if author],
            published_at=_datetime(published),
            description=abstract,
            raw_text=abstract,
            summary=abstract,
            media=[SourceMedia(type="pdf", url=pdf_url)],
            metadata={
                "provider": "arxiv",
                "arxiv_id": arxiv_id,
                "doi": doi or None,
                "pdf_url": pdf_url,
            },
        )

    def _extract_crossref(self, source: RawSource) -> NormalizedSource:
        payload = json.loads(source.content)
        item = payload.get("message", {})
        if not isinstance(item, dict):
            raise SourceError("EXTRACTION_FAILED", "Crossref metadata was invalid")
        doi = str(item.get("DOI") or source.metadata.get("doi"))
        canonical = f"https://doi.org/{doi}"
        title_values = item.get("title") or []
        title = title_values[0] if isinstance(title_values, list) and title_values else doi
        authors = [
            " ".join(filter(None, [author.get("given"), author.get("family")]))
            for author in item.get("author", [])
            if isinstance(author, dict)
        ]
        abstract = re.sub(r"<[^>]+>", " ", str(item.get("abstract") or ""))
        abstract = " ".join(abstract.split())
        date_parts = ((item.get("published") or {}).get("date-parts") or [[]])[0]
        published_at = None
        if date_parts:
            published_at = datetime(
                int(date_parts[0]),
                int(date_parts[1]) if len(date_parts) > 1 else 1,
                int(date_parts[2]) if len(date_parts) > 2 else 1,
            )
        pdf_url = next(
            (
                link.get("URL")
                for link in item.get("link", [])
                if isinstance(link, dict) and link.get("content-type") == "application/pdf"
            ),
            None,
        )
        return NormalizedSource(
            id=stable_source_id(self.source_type, canonical),
            source_type=self.source_type,
            canonical_url=canonical,
            title=str(title),
            authors=authors,
            published_at=published_at,
            description=abstract,
            raw_text=abstract or str(title),
            summary=abstract,
            media=[SourceMedia(type="pdf", url=pdf_url)] if pdf_url else [],
            metadata={
                "provider": "crossref",
                "doi": doi,
                "publisher": item.get("publisher"),
                "container_title": (item.get("container-title") or [None])[0],
                "type": item.get("type"),
                "pdf_url": pdf_url,
            },
            collection_status="PARTIAL" if not abstract else "EXTRACTED",
            limitation_code="ABSTRACT_UNAVAILABLE" if not abstract else None,
            limitation_message="Đã thu thập siêu dữ liệu nhưng không có bản tóm tắt."
            if not abstract
            else None,
        )

    def _extract_doi_csl(self, source: RawSource) -> NormalizedSource:
        item = json.loads(source.content)
        if not isinstance(item, dict):
            raise SourceError("EXTRACTION_FAILED", "DOI metadata was invalid")
        doi = str(item.get("DOI") or source.metadata.get("doi"))
        canonical = f"https://doi.org/{doi}"
        title_value = item.get("title") or doi
        title = title_value[0] if isinstance(title_value, list) else str(title_value)
        authors = [
            " ".join(
                part
                for part in (
                    str(author.get("given") or "").strip(),
                    str(author.get("family") or author.get("literal") or "").strip(),
                )
                if part
            )
            for author in item.get("author", [])
            if isinstance(author, dict)
        ]
        abstract = re.sub(r"<[^>]+>", " ", str(item.get("abstract") or ""))
        abstract = " ".join(abstract.split())
        date_parts = ((item.get("issued") or {}).get("date-parts") or [[]])[0]
        published_at = None
        if date_parts:
            published_at = datetime(
                int(date_parts[0]),
                int(date_parts[1]) if len(date_parts) > 1 else 1,
                int(date_parts[2]) if len(date_parts) > 2 else 1,
            )
        landing_url = str(item.get("URL") or "")
        arxiv = ARXIV_PATTERN.search(landing_url)
        pdf_url = f"https://arxiv.org/pdf/{arxiv.group(1)}.pdf" if arxiv else None
        return NormalizedSource(
            id=stable_source_id(self.source_type, canonical),
            source_type=self.source_type,
            canonical_url=canonical,
            title=title,
            authors=[author for author in authors if author],
            published_at=published_at,
            description=abstract,
            raw_text=abstract or title,
            summary=abstract,
            media=[SourceMedia(type="pdf", url=pdf_url)] if pdf_url else [],
            metadata={
                "provider": "doi_csl",
                "doi": doi,
                "publisher": item.get("publisher"),
                "type": item.get("type"),
                "landing_url": landing_url or None,
                "pdf_url": pdf_url,
            },
            collection_status="PARTIAL" if not abstract else "EXTRACTED",
            limitation_code="ABSTRACT_UNAVAILABLE" if not abstract else None,
            limitation_message="Đã thu thập siêu dữ liệu nhưng không có bản tóm tắt."
            if not abstract
            else None,
        )

    def _extract_semantic_scholar(self, source: RawSource) -> NormalizedSource:
        item = json.loads(source.content)
        canonical = normalize_url(str(item.get("url") or source.final_url))
        abstract = str(item.get("abstract") or "")
        pdf = (item.get("openAccessPdf") or {}).get("url")
        return NormalizedSource(
            id=stable_source_id(self.source_type, canonical),
            source_type=self.source_type,
            canonical_url=canonical,
            title=str(item.get("title") or "Bài báo chưa có tiêu đề"),
            authors=[
                author.get("name") for author in item.get("authors", []) if author.get("name")
            ],
            published_at=_datetime(item.get("publicationDate")),
            description=abstract,
            raw_text=abstract or str(item.get("title") or ""),
            summary=abstract,
            media=[SourceMedia(type="pdf", url=pdf)] if pdf else [],
            metadata={
                "provider": "semantic_scholar",
                "external_ids": item.get("externalIds", {}),
                "pdf_url": pdf,
            },
            collection_status="PARTIAL" if not abstract else "EXTRACTED",
            limitation_code="ABSTRACT_UNAVAILABLE" if not abstract else None,
            limitation_message="Đã thu thập siêu dữ liệu nhưng không có bản tóm tắt."
            if not abstract
            else None,
        )

    def _extract_publisher(self, source: RawSource) -> NormalizedSource:
        parser = CitationParser()
        parser.feed(source.content.decode(source.encoding, errors="replace"))
        meta = parser.meta
        title = (meta.get("citation_title") or meta.get("og:title") or [""])[0]
        abstract = (
            meta.get("citation_abstract")
            or meta.get("description")
            or meta.get("og:description")
            or [""]
        )[0]
        doi = (meta.get("citation_doi") or [None])[0]
        canonical = f"https://doi.org/{doi}" if doi else normalize_url(source.final_url)
        pdf_url = (meta.get("citation_pdf_url") or [None])[0]
        if pdf_url:
            pdf_url = urljoin(source.final_url, pdf_url)
        if not title:
            raise SourceError(
                "EMPTY_CONTENT", "Publisher page did not expose readable paper metadata"
            )
        return NormalizedSource(
            id=stable_source_id(self.source_type, canonical),
            source_type=self.source_type,
            canonical_url=canonical,
            title=title,
            authors=meta.get("citation_author", []),
            published_at=_datetime(
                (meta.get("citation_publication_date") or meta.get("citation_date") or [None])[0]
            ),
            description=abstract,
            raw_text=abstract or title,
            summary=abstract,
            media=[SourceMedia(type="pdf", url=pdf_url)] if pdf_url else [],
            metadata={"provider": "publisher", "doi": doi, "pdf_url": pdf_url},
            collection_status="PARTIAL" if not abstract else "EXTRACTED",
            limitation_code="PAYWALL_OR_METADATA_ONLY" if not abstract else None,
            limitation_message=(
                "Only publisher metadata was available; full text may require subscription access."
                if not abstract
                else None
            ),
        )

    def collect(self, url: str) -> NormalizedSource:
        return self.extract(self.fetch(url))
