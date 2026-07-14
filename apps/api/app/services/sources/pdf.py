import hashlib

from app.schemas.source import NormalizedSource
from app.services.sources.article import parsed_title
from app.services.sources.base import normalize_url, stable_source_id
from app.services.sources.http import fetch_public


class PDFSourceAdapter:
    source_type = "pdf"

    def collect(self, url: str) -> NormalizedSource:
        resource = fetch_public(url, {"application/pdf"})
        canonical = normalize_url(resource.final_url)
        return NormalizedSource(
            id=stable_source_id(self.source_type, canonical),
            source_type=self.source_type,
            canonical_url=canonical,
            title=parsed_title(canonical),
            metadata={
                "content_type": resource.content_type,
                "size_bytes": len(resource.content),
                "sha256": hashlib.sha256(resource.content).hexdigest(),
                "extraction_note": (
                    "Binary captured for validation; a text-layer extractor is not configured. "
                    "OCR must only be used after confirming that no text layer exists."
                ),
            },
            collection_status="NEEDS_TEXT_LAYER",
        )
