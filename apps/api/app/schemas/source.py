from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SourceType = Literal["github", "article", "facebook", "paper", "pdf"]
CollectionStatus = Literal["EXTRACTED", "PARTIAL"]
MediaType = Literal["image", "video", "pdf"]


class SourceEntity(BaseModel):
    id: str
    type: str
    label: str
    confidence: float = Field(default=1, ge=0, le=1)


class SourceClaim(BaseModel):
    id: str
    text: str
    confidence: float = Field(default=1, ge=0, le=1)


class SourceRelationship(BaseModel):
    id: str
    source: str
    target: str
    type: str
    confidence: float = Field(default=1, ge=0, le=1)


class SourceEvidence(BaseModel):
    id: str
    text: str
    page: int | None = None
    section: str | None = None
    timestamp_seconds: float | None = None
    location: str | None = None


class SourceMedia(BaseModel):
    type: MediaType
    url: str


class NormalizedSource(BaseModel):
    id: str
    source_type: SourceType
    canonical_url: str
    title: str
    authors: list[str] = Field(default_factory=list)
    published_at: datetime | None = None
    description: str = ""
    raw_text: str = ""
    summary: str = ""
    language: str = "other"
    media: list[SourceMedia] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    entities: list[SourceEntity] = Field(default_factory=list)
    claims: list[SourceClaim] = Field(default_factory=list)
    relationships: list[SourceRelationship] = Field(default_factory=list)
    evidence: list[SourceEvidence] = Field(default_factory=list)
    collection_status: CollectionStatus = "EXTRACTED"
    limitation_code: str | None = None
    limitation_message: str | None = None


ResearchDocument = NormalizedSource
