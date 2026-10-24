import { api } from "@/lib/api";
import type { GraphFilters, GraphView, KnowledgeGraph } from "./types";

function queryString(values: Record<string, string | number | undefined>) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== "") params.set(key, String(value));
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

type GraphRequest = {
  view?: GraphView;
  rootNodeId?: string;
  depth?: number;
  limit?: number;
};

export function getKnowledgeGraph(filters: GraphFilters, request: GraphRequest = {}) {
  return api<KnowledgeGraph>(
    `/graph${queryString({
      query: filters.query.trim() || undefined,
      node_types: filters.nodeTypes.join(",") || undefined,
      source_types: filters.sourceTypes.join(",") || undefined,
      min_confidence: filters.minConfidence || undefined,
      date_from: filters.dateFrom ? `${filters.dateFrom}T00:00:00Z` : undefined,
      date_to: filters.dateTo ? `${filters.dateTo}T23:59:59Z` : undefined,
      view: request.view,
      root_node_id: request.rootNodeId,
      depth: request.depth,
      limit: request.limit ?? 40,
    })}`,
  );
}

export function getNodeNeighbors(nodeId: string, limit = 15, depth = 1) {
  return api<KnowledgeGraph>(
    `/graph/nodes/${encodeURIComponent(nodeId)}/neighbors${queryString({ limit, depth })}`,
  );
}

export function getSystemKnowledgeGraph() {
  return api<KnowledgeGraph>("/graph/system?limit=1000");
}
