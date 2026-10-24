from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator

AIProviderName = Literal[
    "ollama",
    "openai",
    "deepseek",
    "gemini",
    "openrouter",
    "mistral",
    "claude_code",
    "codex",
    "antigravity",
]


class LinkCreate(BaseModel):
    url: HttpUrl
    source_type: Literal["manual", "discord", "api"] = "manual"
    source_ref: str | None = Field(default=None, max_length=500)
    submitted_by: str = Field(default="local-user", min_length=1, max_length=200)
    provider: AIProviderName | None = None
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


class BulkLinkReview(BaseModel):
    """Decide a batch of queued submissions.

    An empty ``submission_ids`` means "everything currently waiting", which is the common
    case after a collection run and the reason the backlog grew unattended.
    """

    decision: Literal["approve", "reject"]
    submission_ids: list[str] = Field(default_factory=list, max_length=200)


# The states an intake job can be in. Naming them lets a typo in a filter be refused
# instead of returning an empty list that looks like "no data".
LinkSubmissionStatus = Literal[
    "pending",
    "processing",
    "fetching",
    "extracting",
    "analyzing",
    "completed",
    "partial_success",
    "failed",
]


class ReviewBacklog(BaseModel):
    """What is waiting on a human, and the threshold that decides automatic approval.

    Counts are integers. Typing this as a loose mapping made every count come back as a
    float, so a caller rendered "0.0 sources are waiting for a decision".
    """

    needs_review: int = Field(ge=0)
    approved: int = Field(ge=0)
    rejected: int = Field(ge=0)
    duplicate: int = Field(ge=0)
    not_requested: int = Field(ge=0)
    failed: int = Field(ge=0)
    duplicates_awaiting_original: int = Field(ge=0)
    auto_approve_confidence: float = Field(ge=0, le=1)


class BulkLinkReviewResult(BaseModel):
    approved: list[str]
    rejected: list[str]
    skipped: list[dict[str, str]]
    backlog: ReviewBacklog


class TranscriptSegment(BaseModel):
    timestamp_seconds: float = Field(ge=0, le=86_400)
    text: str = Field(min_length=1, max_length=2_000)


class TranscriptUpsert(BaseModel):
    language: str = Field(default="other", min_length=2, max_length=20, pattern=r"^[A-Za-z-]+$")
    segments: list[TranscriptSegment] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_transcript(self) -> "TranscriptUpsert":
        timestamps = [segment.timestamp_seconds for segment in self.segments]
        if timestamps != sorted(timestamps):
            raise ValueError("Transcript timestamps must be in nondecreasing order")
        if sum(len(segment.text) for segment in self.segments) > 120_000:
            raise ValueError("Transcript exceeds the 120000 character limit")
        return self
