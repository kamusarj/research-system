from datetime import datetime

from pydantic import BaseModel, Field


class OntologyNodeRead(BaseModel):
    id: str
    node_type: str
    canonical_label: str
    label_vi: str | None = None
    normalized_key: str
    description: str
    scope_note: str | None = None
    primary_parent_id: str | None = None
    child_count: int = Field(default=0, ge=0)
    lifecycle_status: str
    created_at: datetime
    updated_at: datetime


class OntologyEdgeRead(BaseModel):
    id: str
    source: str
    target: str
    type: str = "PARENT_OF"


class OntologyTreeRead(BaseModel):
    nodes: list[OntologyNodeRead]
    edges: list[OntologyEdgeRead]
    root_ids: list[str]
    seed_version: str = "business-ai-agents-v1"


class PlacementValidationRequest(BaseModel):
    parent_id: str
    node_id: str | None = None


class PlacementValidationRead(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    breadcrumb: list[OntologyNodeRead] = Field(default_factory=list)
