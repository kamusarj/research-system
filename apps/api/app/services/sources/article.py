import re
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from app.schemas.source import NormalizedSource, SourceEvidence, SourceMedia
from app.services.sources.base import RawSource, normalize_url, stable_source_id
from app.services.sources.errors import SourceError
from app.services.sources.http import fetch_public
from app.services.sources.quality import assess_article, meaningful_paragraphs


class ArticleParser(HTMLParser):
    SKIPPED = {"script", "style", "noscript", "svg", "nav", "footer", "aside", "form"}

    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.parts: list[str] = []
        self.headings: list[str] = []
        self.author: str | None = None
        self.published: str | None = None
        self.canonical: str | None = None
        self.description: str | None = None
        self.image: str | None = None
        self.language = "other"
        self._skip = 0
        self._capture_title = False
        self._capture_heading = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.casefold(): value for key, value in attrs}
        if tag in self.SKIPPED:
            self._skip += 1
        if tag == "html" and values.get("lang"):
            self.language = str(values["lang"]).split("-", 1)[0].casefold()
        if tag == "title":
            self._capture_title = True
        if tag in {"h1", "h2", "h3"}:
            self._capture_heading = True
            self.parts.append("\n\n")
        if tag in {"p", "article", "section", "li", "br"}:
            self.parts.append("\n")
        if tag == "meta":
            name = (values.get("name") or values.get("property") or "").casefold()
            content = values.get("content")
            if content and name in {"author", "article:author"}:
                self.author = content
            if content and name in {"description", "og:description", "twitter:description"}:
                self.description = content
            if content and name in {"og:title", "twitter:title"} and not self.title:
                self.title = content
            if content and name in {"og:image", "twitter:image"}:
                self.image = content
            if content and name in {
                "article:published_time",
                "date",
                "datepublished",
                "publish_date",
            }:
                self.published = content
        if tag == "link" and (values.get("rel") or "").casefold() == "canonical":
            self.canonical = values.get("href")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIPPED and self._skip:
            self._skip -= 1
        if tag == "title":
            self._capture_title = False
        if tag in {"h1", "h2", "h3"}:
            self._capture_heading = False

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        value = " ".join(data.split())
        if not value:
            return
        if self._capture_title:
            self.title = f"{self.title} {value}".strip()
        elif self._capture_heading:
            self.headings.append(value)
            self.parts.append(f"## {value}\n")
        else:
            self.parts.append(f"{value} ")

    def markdown(self) -> str:
        return re.sub(r"\n\s*\n\s*\n+", "\n\n", "".join(self.parts)).strip()


def parsed_title(url: str) -> str:
    path = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
    return (
        path.replace("-", " ").replace("_", " ").strip().title()
        or urlparse(url).hostname
        or "Chưa có tiêu đề"
    )


def _published_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class ArticleSourceAdapter:
    source_type = "article"

    def can_handle(self, url: str) -> bool:
        return urlparse(url).scheme in {"http", "https"}

    def fetch(self, url: str) -> RawSource:
        resource = fetch_public(
            url,
            {"text/html", "text/plain", "application/pdf", "application/octet-stream"},
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
        if source.content_type == "text/plain":
            text = source.content.decode(source.encoding, errors="replace").strip()
            if not text:
                raise SourceError("EMPTY_CONTENT", "The source contains no readable text")
            canonical = normalize_url(source.final_url)
            return NormalizedSource(
                id=stable_source_id(self.source_type, canonical),
                source_type=self.source_type,
                canonical_url=canonical,
                title=parsed_title(canonical),
                raw_text=text,
                metadata={"content_type": source.content_type, "headings": []},
            )

        parser = ArticleParser()
        try:
            parser.feed(source.content.decode(source.encoding, errors="replace"))
        except Exception as exc:
            raise SourceError("EXTRACTION_FAILED", "The article HTML could not be parsed") from exc
        canonical_target = (
            urljoin(source.final_url, parser.canonical) if parser.canonical else source.final_url
        )
        canonical = normalize_url(canonical_target)
        text = parser.markdown()
        has_metadata = bool(parser.title or parser.description)
        if not text and not has_metadata:
            raise SourceError("EMPTY_CONTENT", "The page contains no readable content")
        quality = assess_article(text, has_metadata=has_metadata)
        paragraphs = meaningful_paragraphs(text)
        evidence = [
            SourceEvidence(
                id=f"{stable_source_id(self.source_type, canonical)}:evidence:{index}",
                text=paragraph[:600],
                section=next(
                    (heading for heading in reversed(parser.headings) if heading in text), None
                ),
                location=f"paragraph:{index + 1}",
            )
            for index, paragraph in enumerate(paragraphs[:10])
        ]
        return NormalizedSource(
            id=stable_source_id(self.source_type, canonical),
            source_type=self.source_type,
            canonical_url=canonical,
            title=parser.title or parsed_title(canonical),
            authors=[parser.author] if parser.author else [],
            published_at=_published_at(parser.published),
            description=parser.description or "",
            raw_text=text,
            summary=parser.description or "",
            language=parser.language,
            media=(
                [SourceMedia(type="image", url=urljoin(source.final_url, parser.image))]
                if parser.image
                else []
            ),
            metadata={
                "content_type": source.content_type,
                "headings": parser.headings,
                "extracted_chars": len(text),
                "meaningful_paragraphs": len(paragraphs),
                "js_render_suspected": quality.limitation_code == "JS_RENDER_REQUIRED",
            },
            evidence=evidence,
            collection_status=quality.collection_status,
            limitation_code=quality.limitation_code,
            limitation_message=quality.limitation_message,
        )

    def collect(self, url: str) -> NormalizedSource:
        return self.extract(self.fetch(url))
