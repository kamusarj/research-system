from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

MappingAction = Literal[
    "MATCH_EXISTING",
    "CREATE_NEW",
    "ADD_ALIAS",
    "RELATED_BUT_DISTINCT",
    "NEEDS_REVIEW",
]
ReviewDecision = Literal["accepted", "rejected"]


class OntologyCandidateRead(BaseModel):
    node_id: str
    canonical_label: str
    node_type: str
    primary_parent_id: str | None
    matched_by: Literal["canonical_label", "alias", "similarity"]
    score: float = Field(ge=0, le=1)


class GraphMutationRead(BaseModel):
    id: str
    mutation_order: int = Field(ge=0)
    operation: str
    target_kind: str
    target_id: str | None
    before_json: dict[str, Any]
    proposed_json: dict[str, Any]
    validation_status: str
    validation_messages: list[dict[str, Any]]
    review_decision: str
    reviewed_by: str | None
    created_at: datetime
    updated_at: datetime


class GraphChangeSetRead(BaseModel):
    id: str
    origin_type: str
    origin_id: str | None
    title: str
    summary: str
    lifecycle_status: str
    validation_summary: dict[str, Any]
    created_by: str
    approved_by: str | None
    applied_at: datetime | None
    mutations: list[GraphMutationRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class GraphChangeSetList(BaseModel):
    items: list[GraphChangeSetRead]
    total: int = Field(ge=0)


class MutationDecisionRequest(BaseModel):
    decision: ReviewDecision
    proposed_json: dict[str, Any] | None = None


class ChangeSetActionRead(BaseModel):
    id: str
    lifecycle_status: str
    validation_summary: dict[str, Any]
    applied_at: datetime | None = None
