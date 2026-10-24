export type GraphNode = {
  id: string;
  type: string;
  label: string;
  summary: string;
  confidence: number;
  source_count: number;
  published: boolean;
  display_id?: string | null;
  source_type?: string | null;
  source_url?: string | null;
  created_at?: string | null;
  degree: number;
  status?: string | null;
  priority?: number | null;
  primary_parent_id?: string | null;
  child_count?: number;
  workspace_id?: string | null;
  lifecycle_status?: string;
  aliases?: string[];
  provenance?: Record<string, unknown>;
  evidence_count?: number;
  expanded_group?: boolean;
  collapsed_leaf_count?: number;
  leaf_group_expanded?: boolean;
  canonical_node_id?: string | null;
};

export type GraphView = "relationship" | "hierarchy";
export type GraphLayoutMode = GraphView | "orbit";

export type GraphEvidence = {
  text?: string;
  page?: number;
  section?: string;
  timestamp_seconds?: number;
  location?: string;
};

export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  type: string;
  confidence: number;
  evidence_count: number;
  evidence: GraphEvidence[];
};

export type KnowledgeGraph = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  meta: {
    node_count: number;
    edge_count: number;
    query: string | null;
    truncated: boolean;
    provider: string;
    view?: GraphView;
    total_node_count?: number;
    total_edge_count?: number;
    node_limit?: number;
  };
};

export type GraphFilters = {
  query: string;
  nodeTypes: string[];
  sourceTypes: string[];
  minConfidence: number;
  dateFrom: string;
  dateTo: string;
};

export type GraphSelection =
  | { kind: "node"; value: GraphNode }
  | { kind: "edge"; value: GraphEdge }
  | null;

export type OntologyNode = {
  id: string;
  node_type: string;
  canonical_label: string;
  label_vi?: string | null;
  normalized_key: string;
  description: string;
  scope_note?: string | null;
  primary_parent_id?: string | null;
  child_count: number;
  lifecycle_status: string;
  created_at: string;
  updated_at: string;
};
