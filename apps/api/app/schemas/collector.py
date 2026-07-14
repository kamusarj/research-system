from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


class SourceCreate(BaseModel):
    key: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1, max_length=200)
    type: Literal["rss"] = "rss"
    url: HttpUrl
    enabled: bool = True
    auto_approve_threshold: float = Field(default=80, ge=0, le=100)
    auto_reject_threshold: float = Field(default=50, ge=0, le=100)
    config: dict[str, Any] = Field(default_factory=dict)


class SourceUpdate(BaseModel):
    name: str | None = None
    url: HttpUrl | None = None
    enabled: bool | None = None
    auto_approve_threshold: float | None = Field(default=None, ge=0, le=100)
    auto_reject_threshold: float | None = Field(default=None, ge=0, le=100)


class SourceRead(BaseModel):
    id: str
    key: str
    name: str
    type: str
    url: str
    enabled: bool
    auto_approve_threshold: float
    auto_reject_threshold: float
    config: dict[str, Any]
    created_at: datetime


class ReviewUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
