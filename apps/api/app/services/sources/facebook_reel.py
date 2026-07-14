from urllib.parse import urlparse

from app.schemas.source import NormalizedSource
from app.services.sources.base import normalize_url, stable_source_id


class FacebookReelSourceAdapter:
    source_type = "facebook_reel"

    def collect(self, url: str) -> NormalizedSource:
        # Facebook HTML is intentionally not scraped. A transcript can be supplied by a user later.
        canonical = normalize_url(url)
        reel_id = next(
            (part for part in reversed(urlparse(canonical).path.split("/")) if part),
            "unknown",
        )
        return NormalizedSource(
            id=stable_source_id(self.source_type, canonical),
            source_type=self.source_type,
            canonical_url=canonical,
            title=f"Facebook Reel {reel_id}",
            metadata={
                "needs_transcript": True,
                "transcript_source": None,
                "timestamp_evidence_required": True,
            },
            collection_status="NEEDS_TRANSCRIPT",
        )
