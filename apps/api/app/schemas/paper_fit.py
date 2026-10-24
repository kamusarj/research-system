from typing import Literal

from pydantic import BaseModel, Field

PaperFitDecision = Literal[
    "hard_gate_failed",
    "not_relevant",
    "watch",
    "draft_graph",
    "priority_review",
]


class PaperFitHardGates(BaseModel):
    supported_access: bool = True
    readable_content: bool = True
    not_duplicate: bool = True
    has_title: bool = True
    has_provenance: bool = True
    supported_language: bool = True
    safe_file: bool = True
    content_valid: bool = True


class PaperFitDimensions(BaseModel):
    system_fit: float = Field(ge=0, le=100)
    business_applicability: float = Field(ge=0, le=100)
    evidence_quality: float = Field(ge=0, le=100)
    novelty: float = Field(ge=0, le=100)
    implementation_value: float = Field(ge=0, le=100)
    gap_coverage: float = Field(ge=0, le=100)
    freshness: float = Field(ge=0, le=100)


class PaperFitAssessment(BaseModel):
    hard_gates: PaperFitHardGates = Field(default_factory=PaperFitHardGates)
    dimensions: PaperFitDimensions
    matched_pillars: list[str] = Field(default_factory=list)
    candidate_parents: list[str] = Field(default_factory=list)
    contribution_types: list[str] = Field(default_factory=list)
    overlaps_with: list[str] = Field(default_factory=list)
    fills_gaps: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    reasoning_summary: str = Field(default="", max_length=2000)
    confidence: float = Field(default=0, ge=0, le=1)


class PaperFitProviderAssessment(BaseModel):
    """Provider-supplied semantic inputs; hard gates and totals remain server-owned."""

    dimensions: PaperFitDimensions
    detected_language: str = Field(default="unknown", max_length=24)
    matched_pillars: list[str] = Field(default_factory=list, max_length=11)
    candidate_parents: list[str] = Field(default_factory=list, max_length=12)
    contribution_types: list[str] = Field(default_factory=list, max_length=12)
    overlaps_with: list[str] = Field(default_factory=list, max_length=12)
    fills_gaps: list[str] = Field(default_factory=list, max_length=12)
    limitations: list[str] = Field(default_factory=list, max_length=12)
    reasoning_summary: str = Field(default="", max_length=2000)
    confidence: float = Field(default=0, ge=0, le=1)


class PaperFitResult(BaseModel):
    rubric_version: str
    fit_score: float | None
    decision: PaperFitDecision
    failed_gates: list[str] = Field(default_factory=list)
    dimensions: PaperFitDimensions
    matched_pillars: list[str] = Field(default_factory=list)
    candidate_parents: list[str] = Field(default_factory=list)
    contribution_types: list[str] = Field(default_factory=list)
    overlaps_with: list[str] = Field(default_factory=list)
    fills_gaps: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    reasoning_summary: str = ""
    confidence: float = Field(ge=0, le=1)
