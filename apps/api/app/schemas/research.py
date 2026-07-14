from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

ResearchType = Literal["internal-research", "reference", "deep-research-report"]
ResearchStatus = Literal["draft", "in-review", "approved", "archived", "rejected"]
CollectionMethod = Literal["manual", "auto-collected", "ai-researched"]
RelationType = Literal[
    "references",
    "extends",
    "supports",
    "contradicts",
]


class ResearchCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    type: ResearchType = "internal-research"
    collection_method: CollectionMethod = "manual"
    summary: str | None = None
    content: str = ""
    source_url: HttpUrl | None = None
    external_id: str | None = None
    authors: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tags")
    @classmethod
    def unique_tags(cls, tags: list[str]) -> list[str]:
        return list(dict.fromkeys(tag.strip() for tag in tags if tag.strip()))


class ResearchUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    type: ResearchType | None = None
    collection_method: CollectionMethod | None = None
    summary: str | None = None
    content: str | None = None
    source_url: HttpUrl | None = None
    authors: list[str] | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class ResearchRead(BaseModel):
    id: str
    display_id: str
    title: str
    type: str
    status: ResearchStatus
    collection_method: str
    summary: str | None
    content: str
    source_url: str | None
    authors: list[str]
    tags: list[str]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None


class ResearchList(BaseModel):
    items: list[ResearchRead]
    total: int
    page: int
    page_size: int


class VersionRead(BaseModel):
    id: str
    version_number: int
    snapshot: dict[str, Any]
    created_at: datetime


class CommentCreate(BaseModel):
    body: str = Field(min_length=1)
    author: str = Field(default="Local researcher", min_length=1, max_length=120)


class CommentRead(CommentCreate):
    id: str
    research_id: str
    created_at: datetime


class RelationCreate(BaseModel):
    target_id: str
    relation_type: RelationType
    confidence: float | None = Field(default=None, ge=0, le=1)
    reasoning: str | None = None


class RelationRead(BaseModel):
    id: str
    source_id: str
    target_id: str
    relation_type: str
    discovered_by: str
    confidence: float | None
    reasoning: str | None
    created_at: datetime


class AttachmentCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=500)
    object_key: str = Field(min_length=1, max_length=1000)
    mime_type: str = Field(min_length=1, max_length=200)
    size_bytes: int = Field(ge=0)


class AttachmentRead(AttachmentCreate):
    id: str
    research_id: str
    created_at: datetime
