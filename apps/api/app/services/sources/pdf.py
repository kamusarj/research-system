import hashlib
import io
from urllib.parse import urlparse

from pypdf import PdfReader

from app.core.config import settings
from app.schemas.source import NormalizedSource, SourceEvidence, SourceMedia
from app.services.ocr import ocr_pdf
from app.services.sources.article import parsed_title
from app.services.sources.base import RawSource, normalize_url, stable_source_id
from app.services.sources.errors import SourceError
from app.services.sources.http import fetch_public


class PDFSourceAdapter:
    source_type = "pdf"

    def can_handle(self, url: str) -> bool:
        return urlparse(url).path.casefold().endswith(".pdf")

    def fetch(self, url: str) -> RawSource:
        resource = fetch_public(
            url,
            {"application/pdf", "application/octet-stream"},
            max_bytes=settings.intake_max_pdf_bytes,
        )
        if not resource.content.startswith(b"%PDF"):
            raise SourceError("UNSUPPORTED_CONTENT_TYPE", "The URL did not return a valid PDF")
        return RawSource(
            requested_url=url,
            final_url=resource.final_url,
            content_type="application/pdf",
            content=resource.content,
            encoding="binary",
            status_code=resource.status_code,
            headers=resource.headers or {},
        )

    def extract(self, source: RawSource) -> NormalizedSource:
        canonical = normalize_url(source.final_url)
        try:
            reader = PdfReader(io.BytesIO(source.content), strict=False)
        except Exception as exc:
            raise SourceError(
                "PDF_PARSE_FAILED", "The PDF is damaged, encrypted, or unsupported"
            ) from exc
        total_pages = len(reader.pages)
        pages_to_read = min(total_pages, settings.intake_pdf_max_pages)
        text_parts: list[str] = []
        evidence: list[SourceEvidence] = []
        for index in range(pages_to_read):
            try:
                page_text = (reader.pages[index].extract_text() or "").strip()
            except Exception as exc:
                raise SourceError(
                    "PDF_PARSE_FAILED", f"PDF text extraction failed on page {index + 1}"
                ) from exc
            if page_text:
                text_parts.append(page_text)
                if len(evidence) < 12:
                    evidence.append(
                        SourceEvidence(
                            id=f"{stable_source_id(self.source_type, canonical)}:page:{index + 1}",
                            text=page_text[:800],
                            page=index + 1,
                            location=f"page:{index + 1}",
                        )
                    )
        raw_text = "\n\n".join(text_parts).strip()
        pdf_metadata = reader.metadata or {}
        title = str(pdf_metadata.get("/Title") or parsed_title(canonical)).strip()
        author = str(pdf_metadata.get("/Author") or "").strip()
        no_text_layer = not raw_text
        truncated = total_pages > pages_to_read
        ocr_result = None
        if no_text_layer:
            ocr_result = ocr_pdf(source.content)
            if ocr_result.text:
                raw_text = ocr_result.text
                evidence = [
                    SourceEvidence(
                        id=f"{stable_source_id(self.source_type, canonical)}:ocr:{page.page}",
                        text=page.text[:800],
                        page=page.page,
                        location=f"page:{page.page}",
                    )
                    for page in ocr_result.pages[:12]
                ]
        limitation_code = (
            ocr_result.limitation_code
            if ocr_result is not None
            else "PDF_PAGE_LIMIT"
            if truncated
            else None
        )
        limitation_message = (
            ocr_result.limitation_message
            if ocr_result is not None
            else f"Only the first {pages_to_read} pages were extracted."
            if truncated
            else None
        )
        return NormalizedSource(
            id=stable_source_id(self.source_type, canonical),
            source_type=self.source_type,
            canonical_url=canonical,
            title=title,
            authors=[author] if author else [],
            raw_text=raw_text,
            media=[SourceMedia(type="pdf", url=canonical)],
            metadata={
                "content_type": source.content_type,
                "size_bytes": len(source.content),
                "sha256": hashlib.sha256(source.content).hexdigest(),
                "page_count": total_pages,
                "pages_extracted": pages_to_read,
                "page_limit": settings.intake_pdf_max_pages,
                "truncated": truncated,
                "has_text_layer": not no_text_layer,
                "ocr_applied": bool(ocr_result and ocr_result.text),
                "ocr_engine": "tesseract" if ocr_result and ocr_result.text else None,
                "ocr_languages": settings.ocr_languages if ocr_result and ocr_result.text else None,
                "ocr_pages_attempted": ocr_result.pages_attempted if ocr_result else 0,
            },
            evidence=evidence,
            collection_status="PARTIAL" if limitation_code else "EXTRACTED",
            limitation_code=limitation_code,
            limitation_message=limitation_message,
        )

    def collect(self, url: str) -> NormalizedSource:
        return self.extract(self.fetch(url))
