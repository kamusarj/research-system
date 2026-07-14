import { api } from "@/lib/api";
import type { GraphFilters, KnowledgeGraph } from "./types";

function queryString(values: Record<string, string | number | undefined>) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== "") params.set(key, String(value));
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function getKnowledgeGraph(filters: GraphFilters, limit = 40) {
  return api<KnowledgeGraph>(
    `/graph${queryString({
      query: filters.query.trim() || undefined,
      node_types: filters.nodeTypes.join(",") || undefined,
      source_types: filters.sourceTypes.join(",") || undefined,
      min_confidence: filters.minConfidence || undefined,
      date_from: filters.dateFrom ? `${filters.dateFrom}T00:00:00Z` : undefined,
      date_to: filters.dateTo ? `${filters.dateTo}T23:59:59Z` : undefined,
      limit,
    })}`,
  );
}

export function getNodeNeighbors(nodeId: string, limit = 15, depth = 1) {
  return api<KnowledgeGraph>(
    `/graph/nodes/${encodeURIComponent(nodeId)}/neighbors${queryString({ limit, depth })}`,
  );
}
