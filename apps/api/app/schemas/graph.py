from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class GraphNode(BaseModel):
    id: str = Field(min_length=1)
    type: str = Field(min_length=1)
    label: str = Field(min_length=1)
    summary: str = ""
    confidence: float = Field(default=1, ge=0, le=1)
    source_count: int = Field(default=1, ge=0)
    published: bool = True
    display_id: str | None = None
    source_type: str | None = None
    source_url: str | None = None
    created_at: datetime | None = None
    degree: int = Field(default=0, ge=0)
    status: str | None = None
    priority: int | None = None
    primary_parent_id: str | None = None
    child_count: int = Field(default=0, ge=0)
    workspace_id: str | None = None
    lifecycle_status: str = "approved"
    aliases: list[str] = Field(default_factory=list)
    provenance: dict[str, object] = Field(default_factory=dict)
    evidence_count: int = Field(default=0, ge=0)
    # Set when a relationship-view node is the same thing as an approved ontology node, so
    # the two views agree on identity instead of showing one concept as two nodes.
    canonical_node_id: str | None = None


class GraphEdge(BaseModel):
    id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    type: str = Field(min_length=1)
    confidence: float = Field(default=1, ge=0, le=1)
    evidence_count: int = Field(default=0, ge=0)
    evidence: list[dict[str, object]] = Field(default_factory=list)


class GraphMeta(BaseModel):
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    query: str | None = None
    truncated: bool = False
    provider: str = "postgres"
    view: Literal["relationship", "hierarchy"] = "relationship"
    # How many nodes and edges matched before the response limit was applied. "Truncated"
    # alone tells a reader that something was hidden but not how much, which is the
    # difference between a graph they can trust and one they cannot.
    total_node_count: int = Field(default=0, ge=0)
    total_edge_count: int = Field(default=0, ge=0)
    node_limit: int = Field(default=0, ge=0)


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    meta: GraphMeta

    @model_validator(mode="after")
    def validate_graph(self) -> "GraphResponse":
        node_ids = [node.id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Graph contains duplicate node IDs")
        edge_ids = [edge.id for edge in self.edges]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("Graph contains duplicate edge IDs")
        available = set(node_ids)
        for edge in self.edges:
            if edge.source == edge.target:
                raise ValueError(f"Graph edge {edge.id} is an unintended self-loop")
            if edge.source not in available or edge.target not in available:
                raise ValueError(f"Graph edge {edge.id} references a missing node")
        if self.meta.node_count != len(self.nodes) or self.meta.edge_count != len(self.edges):
            raise ValueError("Graph metadata counts do not match the response")
        return self


class GraphQuery(BaseModel):
    query: str | None = None
    node_types: set[str] = Field(default_factory=set)
    source_types: set[str] = Field(default_factory=set)
    min_confidence: float = Field(default=0, ge=0, le=1)
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = Field(ge=1)
    depth: int = Field(default=1, ge=1)
    root_node_id: str | None = None
    view: Literal["relationship", "hierarchy"] = "relationship"
