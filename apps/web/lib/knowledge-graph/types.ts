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
};

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
