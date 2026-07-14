from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class LinkCreate(BaseModel):
    url: HttpUrl
    source_type: Literal["manual", "discord", "api"] = "manual"
    source_ref: str | None = Field(default=None, max_length=500)
    submitted_by: str = Field(default="local-user", min_length=1, max_length=200)
    provider: Literal[
        "mock", "ollama", "openai", "deepseek", "gemini", "openrouter", "mistral"
    ] | None = None
    auto_approve: bool = False


class LinkClassification(BaseModel):
    content_type: Literal["article", "paper", "documentation", "repository", "case-study", "other"]
    language: Literal["en", "vi", "other"]
    summary: str
    concepts: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    agent_patterns: list[str] = Field(default_factory=list)
    business_domains: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    relations: list[dict[str, str]] = Field(default_factory=list)
    relevance_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    reasoning: str


class LinkReview(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    summary: str | None = None
    tags: list[str] | None = None
