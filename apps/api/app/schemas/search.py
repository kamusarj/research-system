from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class SearchDocument(BaseModel):
    id: str = Field(min_length=1, max_length=36)
    display_id: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=500)
    summary: str = ""
    content: str = ""
    type: str = Field(min_length=1, max_length=40)
    collection_method: str = Field(min_length=1, max_length=30)
    authors: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    tag_keys: list[str] = Field(default_factory=list)
    source_url: HttpUrl | None = None
    created_at: datetime
    updated_at: datetime
    approved_at: datetime


class SearchRebuildRequest(BaseModel):
    projections: list[Literal["meilisearch", "pgvector"]] = Field(
        default_factory=lambda: ["meilisearch", "pgvector"], min_length=1, max_length=2
    )

    @field_validator("projections")
    @classmethod
    def unique_projections(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("Projection names must be unique")
        return values


class ProjectionCount(BaseModel):
    source: int = Field(ge=0)
    projected: int = Field(ge=0)
    chunks: int | None = Field(default=None, ge=0)
    provider: str
    model: str | None = None


class SearchRebuildResponse(BaseModel):
    projections: dict[str, ProjectionCount]


class SemanticSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2_000)

    @field_validator("query")
    @classmethod
    def non_empty_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Search query must not be blank")
        return value


class HybridSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2_000)
    limit: int = Field(default=20, ge=1, le=100)
    type: str | None = Field(default=None, max_length=40)
    collection_method: str | None = Field(default=None, max_length=30)
    tag: str | None = Field(default=None, max_length=60)

    @field_validator("query")
    @classmethod
    def non_empty_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Search query must not be blank")
        return value


def reciprocal_rank_fusion(rank_lists: list[list[str]], *, k: int = 60) -> list[str]:
    """Fuse multiple ranked id lists by Reciprocal Rank Fusion.

    ``score = sum(1 / (k + rank + 1))`` for each list a candidate appears in.
    Ties are broken by canonical id so the order is deterministic. Empty input
    returns an empty list; lists with no overlap still fuse because an item only
    needs to appear in one list, not all of them, to retain its score.
    """
    if not rank_lists:
        return []
    k = max(1, min(k, 10_000))
    scores: dict[str, float] = {}
    for ranked in rank_lists:
        for rank, item_id in enumerate(ranked):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
    return [item_id for item_id, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))]
