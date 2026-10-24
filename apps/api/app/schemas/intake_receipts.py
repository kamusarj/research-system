from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.schemas.ingestion import AIProviderName


class ReceiptMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    event_type: Literal["manual_submit", "api_request", "message"] | None = None


class ReceiptSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["manual", "api", "discord"]
    namespace: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    occurrence_ref: str = Field(min_length=1, max_length=500)
    container_ref: str | None = Field(default=None, min_length=1, max_length=200)
    external_actor_ref: str | None = Field(default=None, min_length=1, max_length=500)
    metadata: ReceiptMetadata = Field(default_factory=ReceiptMetadata)

    @field_validator("occurrence_ref", "container_ref", "external_actor_ref")
    @classmethod
    def bounded_opaque_ref(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized or any(ord(char) < 32 for char in normalized):
            raise ValueError("Source references must be non-empty printable values")
        return normalized


class ReceiptURLItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["url"] = "url"
    url: HttpUrl
    provider: AIProviderName | None = None
    auto_approve: bool = False


class ReceiptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: ReceiptSource
    items: list[ReceiptURLItemCreate] = Field(default_factory=list, max_length=20)


class KnowledgeGapSummary(BaseModel):
    id: str
    title: str
    concept_key: str
    status: Literal["detected", "prioritized", "assigned"]
    priority: int
    coverage_count: int
    reason: str


class ReceiptItemRead(BaseModel):
    id: str
    ordinal: int = Field(ge=1)
    kind: Literal["url", "document"]
    disposition: Literal["queued", "linked_existing", "replayed"]
    initial_disposition: Literal["queued", "linked_existing"]
    normalized_url: str | None = None
    link_submission_id: str | None = None
    document_workspace_id: str | None = None
    status: str
    review_status: str
    research_id: str | None = None
    error_code: str | None = None
    knowledge_gaps: list[KnowledgeGapSummary] = Field(default_factory=list)


class ReceiptRead(BaseModel):
    id: str
    source_type: Literal["manual", "api", "discord"]
    source_namespace: str
    external_occurrence_ref: str
    container_ref: str | None = None
    replayed: bool
    status: str
    delivery_count: int = Field(ge=1)
    received_at: datetime
    last_seen_at: datetime
    items: list[ReceiptItemRead]
