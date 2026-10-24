from pydantic import BaseModel, Field


class FeatureFlagsRead(BaseModel):
    graph_v2: bool
    document_workspaces: bool
    graph_chat: bool
    rate_limits: bool
    research_agent: bool = False


class GraphInvariantReport(BaseModel):
    valid: bool
    checked_nodes: int = 0
    checked_edges: int = 0
    checked_aliases: int = 0
    errors: list[str] = Field(default_factory=list)


class SystemReadinessRead(BaseModel):
    status: str
    features: FeatureFlagsRead
    graph: GraphInvariantReport
