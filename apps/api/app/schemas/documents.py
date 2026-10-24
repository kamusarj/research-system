from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.graph_changes import GraphChangeSetRead
from app.schemas.paper_fit import PaperFitDecision

DocumentNodeType = Literal[
    "document",
    "section",
    "claim",
    "evidence",
    "limitation",
    "method",
    "dataset",
    "metric",
    "finding",
    "concept",
    "technology",
    "agent_pattern",
    "business_use_case",
    "citation",
]


class LatexCompileRequest(BaseModel):
    source: str = Field(min_length=1, max_length=200_000)


class DocumentEvidenceProposal(BaseModel):
    excerpt: str = Field(min_length=1, max_length=800)
    section_heading: str | None = Field(default=None, max_length=300)
    page: int | None = Field(default=None, ge=1)


class DocumentGraphNodeProposal(BaseModel):
    local_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    node_type: DocumentNodeType
    label: str = Field(min_length=1, max_length=250)
    summary: str = Field(default="", max_length=1500)
    parent_local_id: str | None = Field(default=None, max_length=80)
    confidence: float = Field(default=0, ge=0, le=1)
    evidence: list[DocumentEvidenceProposal] = Field(default_factory=list, max_length=5)


class DocumentGraphEdgeProposal(BaseModel):
    source_local_id: str = Field(max_length=80)
    target_local_id: str = Field(max_length=80)
    edge_type: str = Field(min_length=1, max_length=60)
    confidence: float = Field(default=0, ge=0, le=1)
    evidence: list[DocumentEvidenceProposal] = Field(default_factory=list, max_length=5)


class DocumentGraphExtraction(BaseModel):
    nodes: list[DocumentGraphNodeProposal] = Field(default_factory=list, max_length=80)
    edges: list[DocumentGraphEdgeProposal] = Field(default_factory=list, max_length=120)
    limitations: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_graph(self):
        ids = [node.local_id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("Document graph node IDs must be unique")
        visible = set(ids)
        for node in self.nodes:
            if node.parent_local_id is not None and node.parent_local_id not in visible:
                raise ValueError("Document graph parent must reference a visible node")
            if node.parent_local_id == node.local_id:
                raise ValueError("Document graph node cannot parent itself")
        for edge in self.edges:
            if edge.source_local_id not in visible or edge.target_local_id not in visible:
                raise ValueError("Document graph edge must reference visible nodes")
            if edge.source_local_id == edge.target_local_id:
                raise ValueError("Document graph self-loops are not allowed")
        return self


DocumentResearchComparison = Literal["consistent", "different", "insufficient"]


class DocumentNodeResearchProposal(BaseModel):
    node_id: str = Field(min_length=1, max_length=36)
    research_summary: str = Field(min_length=1, max_length=1200)
    comparison_status: DocumentResearchComparison
    difference_summary: str = Field(default="", max_length=1200)
    confidence: float = Field(default=0, ge=0, le=1)

    @model_validator(mode="after")
    def validate_difference(self):
        if self.comparison_status == "different" and not self.difference_summary.strip():
            raise ValueError("Different research must explain the difference")
        return self


class DocumentGraphResearchExtraction(BaseModel):
    results: list[DocumentNodeResearchProposal] = Field(min_length=1, max_length=80)

    @model_validator(mode="after")
    def validate_unique_node_ids(self):
        node_ids = [item.node_id for item in self.results]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Document research node IDs must be unique")
        return self


class DocumentNodeAIResearchRead(BaseModel):
    research_summary: str
    comparison_status: DocumentResearchComparison
    difference_summary: str = ""
    confidence: float = Field(ge=0, le=1)
    provider_name: str
    model_name: str
    prompt_version: str
    researched_at: datetime


class PaperEvaluationRead(BaseModel):
    id: str
    rubric_version: str
    dimension_scores: dict[str, float]
    fit_score: float | None
    decision: PaperFitDecision
    failed_gates: list[str]
    matched_pillars: list[str]
    candidate_parents: list[str]
    contribution_types: list[str]
    overlaps_with: list[str]
    fills_gaps: list[str]
    limitations: list[str]
    reasoning_summary: str
    confidence: float
    provider_name: str | None
    model_name: str | None
    prompt_version: str | None
    created_at: datetime


class DocumentGraphEvidenceRead(BaseModel):
    id: str
    location: dict[str, object]
    excerpt: str | None
    extraction_method: str | None


class DocumentGraphNodeRead(BaseModel):
    id: str
    node_type: DocumentNodeType
    label: str
    summary: str
    parent_node_id: str | None
    confidence: float
    evidence_status: str
    evidence: list[DocumentGraphEvidenceRead] = Field(default_factory=list)
    ai_research: DocumentNodeAIResearchRead | None = None


class DocumentGraphEdgeRead(BaseModel):
    id: str
    source_node_id: str
    target_node_id: str
    edge_type: str
    confidence: float
    evidence_status: str
    evidence: list[DocumentGraphEvidenceRead] = Field(default_factory=list)


class DocumentGraphRead(BaseModel):
    workspace_id: str
    nodes: list[DocumentGraphNodeRead]
    edges: list[DocumentGraphEdgeRead]
    meta: dict[str, object]


class DocumentGraphResearchRequest(BaseModel):
    node_ids: list[str] = Field(default_factory=list, max_length=80)
    create_change_set: bool = False
    provider: str | None = Field(default=None, max_length=40)

    @field_validator("node_ids")
    @classmethod
    def validate_node_ids(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("Research node IDs must be unique")
        if any(not value or len(value) > 36 for value in values):
            raise ValueError("Research node ID is invalid")
        return values


class DocumentGraphResearchRead(BaseModel):
    graph: DocumentGraphRead
    change_set: GraphChangeSetRead | None = None


class DocumentWorkspaceRead(BaseModel):
    id: str
    research_id: str
    attachment_id: str
    filename: str
    summary: str = Field(default="", max_length=500)
    mime_type: str
    size_bytes: int = Field(ge=0)
    content_hash: str
    processing_status: str
    review_status: str
    extraction_limitations: list[dict[str, object]] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    provider_name: str | None = None
    model_name: str | None = None
    attempt_count: int = Field(default=0, ge=0)
    next_attempt_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    extracted_char_count: int = Field(default=0, ge=0)
    graph_node_count: int = Field(default=0, ge=0)
    graph_edge_count: int = Field(default=0, ge=0)
    source_version: int = Field(default=1, ge=1)
    editable: bool = False
    rag_status: str = "pending"
    rag_chunk_count: int = Field(default=0, ge=0)
    rag_indexed_version: int | None = Field(default=None, ge=1)
    rag_error_code: str | None = None
    rag_indexed_at: datetime | None = None
    evaluation: PaperEvaluationRead | None = None
    created_at: datetime
    updated_at: datetime


class DocumentWorkspaceList(BaseModel):
    items: list[DocumentWorkspaceRead]
    total: int = Field(ge=0)


class DocumentContentRead(BaseModel):
    workspace_id: str
    filename: str
    format: str
    preview_kind: str
    source_text: str | None = None
    extracted_text: str
    supports_raw: bool
    source_truncated: bool = False
    editable: bool = False
    source_version: int = Field(default=1, ge=1)
    editing_representation: str = "source"
    original_available: bool = False
    original_preview_kind: str | None = None


class DocumentSourceSaveRequest(BaseModel):
    base_version: int = Field(ge=1)
    content: str = Field(min_length=1, max_length=2_000_000)
    change_summary: str | None = Field(default=None, max_length=500)


class DocumentSourceRestoreRequest(BaseModel):
    base_version: int = Field(ge=1)


class DocumentSourceVersionRead(BaseModel):
    id: str
    version_number: int = Field(ge=1)
    content_hash: str
    size_bytes: int = Field(ge=0)
    origin: str
    change_summary: str | None = None
    created_by: str
    created_at: datetime
    current: bool = False


class DocumentSourceVersionList(BaseModel):
    items: list[DocumentSourceVersionRead]
    total: int = Field(ge=0)


DocumentAIEditAction = Literal["improve", "shorten", "expand", "fix_grammar", "custom"]


class DocumentAIEditCreateRequest(BaseModel):
    base_version: int = Field(ge=1)
    selection_start: int = Field(ge=0)
    selection_end: int = Field(gt=0)
    action: DocumentAIEditAction
    instruction: str | None = Field(default=None, max_length=1000)
    provider: str | None = Field(default=None, max_length=40)

    @model_validator(mode="after")
    def validate_selection_and_instruction(self):
        if self.selection_end <= self.selection_start:
            raise ValueError("Selection end must be after selection start")
        if self.selection_end - self.selection_start > 20_000:
            raise ValueError("Selection cannot exceed 20,000 characters")
        if self.action == "custom" and not (self.instruction or "").strip():
            raise ValueError("Custom edits require an instruction")
        return self


class DocumentAIEditRead(BaseModel):
    id: str
    workspace_id: str
    base_version: int = Field(ge=1)
    selection_start: int = Field(ge=0)
    selection_end: int = Field(gt=0)
    action: str
    instruction: str | None = None
    original_text: str
    replacement_text: str
    explanation: str
    provider_name: str
    model_name: str
    status: str
    accepted_version_number: int | None = None
    created_at: datetime


class DocumentRagStatusRead(BaseModel):
    status: str
    chunk_count: int = Field(ge=0)
    indexed_version: int | None = Field(default=None, ge=1)
    error_code: str | None = None
    indexed_at: datetime | None = None


class DocumentBrainstormMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4_000)

    @field_validator("content")
    @classmethod
    def strip_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Brainstorm messages cannot be blank")
        return stripped


class DocumentBrainstormRequest(BaseModel):
    source: str = Field(min_length=1, max_length=2_000_000)
    message: str = Field(min_length=1, max_length=4_000)
    history: list[DocumentBrainstormMessage] = Field(default_factory=list, max_length=10)
    selection_start: int | None = Field(default=None, ge=0)
    selection_end: int | None = Field(default=None, gt=0)
    provider: Literal["openai", "deepseek", "claude_code", "codex", "antigravity"] | None = None

    @field_validator("message")
    @classmethod
    def strip_user_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Brainstorm message cannot be blank")
        return stripped

    @model_validator(mode="after")
    def validate_selection_and_history(self):
        paired = self.selection_start is not None and self.selection_end is not None
        if (self.selection_start is None) != (self.selection_end is None):
            raise ValueError("Selection start and end must be supplied together")
        if paired:
            assert self.selection_start is not None and self.selection_end is not None
            if self.selection_end <= self.selection_start:
                raise ValueError("Selection end must be after selection start")
            if self.selection_end > len(self.source):
                raise ValueError("Selection is outside the current document")
            if self.selection_end - self.selection_start > 20_000:
                raise ValueError("Selection cannot exceed 20,000 characters")
        if sum(len(item.content) for item in self.history) > 20_000:
            raise ValueError("Brainstorm history cannot exceed 20,000 characters")
        return self


class DocumentBrainstormRead(BaseModel):
    content: str
    provider_name: str
    model_name: str
    source_context_truncated: bool = False


DocumentInstantEditAction = Literal[
    "improve",
    "shorten",
    "expand",
    "fix_grammar",
    "tone",
    "translate",
    "bullets",
    "table",
    "custom",
]


class DocumentInstantEditRequest(BaseModel):
    source: str = Field(min_length=1, max_length=2_000_000)
    source_revision: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9:_-]+$")
    selection_start: int = Field(ge=0)
    selection_end: int = Field(gt=0)
    action: DocumentInstantEditAction
    instruction: str | None = Field(default=None, max_length=1_000)
    source_format: str | None = Field(default=None, max_length=40)
    provider: Literal["openai", "deepseek", "claude_code", "codex", "antigravity"] | None = None

    @model_validator(mode="after")
    def validate_instant_edit(self):
        if self.selection_end <= self.selection_start:
            raise ValueError("Selection end must be after selection start")
        if self.selection_end > len(self.source):
            raise ValueError("Selection is outside the current document")
        if self.selection_end - self.selection_start > 20_000:
            raise ValueError("Selection cannot exceed 20,000 characters")
        if not self.source[self.selection_start : self.selection_end].strip():
            raise ValueError("Select non-empty text before using AI")
        if self.action == "custom" and not (self.instruction or "").strip():
            raise ValueError("Custom edits require an instruction")
        return self


class DocumentInstantEditRead(BaseModel):
    source_revision: str
    selection_start: int = Field(ge=0)
    selection_end: int = Field(gt=0)
    original_text_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    replacement_text: str = Field(min_length=1, max_length=40_000)
    explanation: str = Field(default="", max_length=1_000)
    risk: Literal["low", "medium", "high"]
    auto_apply_allowed: bool
    warnings: list[str] = Field(default_factory=list, max_length=8)
    provider_name: str
    model_name: str
