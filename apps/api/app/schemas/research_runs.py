from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ResearchRunCreate(BaseModel):
    question: str = Field(min_length=10, max_length=1000)
    knowledge_gap_id: str | None = Field(default=None, max_length=36)
    variant: Literal["optimized", "naive"] = "optimized"

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 10:
            raise ValueError("Câu hỏi cần ít nhất 10 ký tự")
        return value


class ResearchRunEventRead(BaseModel):
    id: int
    kind: str
    stage: str
    message: str
    data: dict[str, Any]
    created_at: datetime


class ResearchRunSourceRead(BaseModel):
    id: str
    provider: str
    perspective: str
    url: str
    domain: str
    title: str
    status: str
    suspicious: bool
    citation_index: int | None
    error_code: str | None


class ResearchRunClaimRead(BaseModel):
    id: str
    source_id: str
    perspective: str
    text: str
    quote: str
    matched_quote: str | None
    match_method: str
    entailment: str
    status: str
    reason: str | None
    used_in_report: bool


class ResearchRunRead(BaseModel):
    id: str
    question: str
    status: str
    stage: str
    variant: str
    provider_name: str | None
    model_name: str | None
    knowledge_gap_id: str | None
    report_research_id: str | None
    error_code: str | None
    error_message: str | None
    metrics: dict[str, Any]
    created_by: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class ResearchRunDetail(ResearchRunRead):
    report_markdown: str | None
    sources: list[ResearchRunSourceRead]
    claims: list[ResearchRunClaimRead]
    events: list[ResearchRunEventRead]


class ResearchRunList(BaseModel):
    items: list[ResearchRunRead]
    total: int
