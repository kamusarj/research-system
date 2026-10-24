"use client";

import { useCallback, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getKnowledgeGraph, getNodeNeighbors } from "@/lib/knowledge-graph/graph-api";
import { mergeKnowledgeGraphs } from "@/lib/knowledge-graph/graph-mapper";
import type {
  GraphFilters,
  GraphView,
  KnowledgeGraph,
} from "@/lib/knowledge-graph/types";

export const defaultGraphFilters: GraphFilters = {
  query: "",
  nodeTypes: [],
  sourceTypes: [],
  minConfidence: 0,
  dateFrom: "",
  dateTo: "",
};

export const GRAPH_QUERY_STALE_TIME_MS = 30_000;
export const GRAPH_QUERY_GC_TIME_MS = 5 * 60_000;

type GraphOptions = {
  view?: GraphView;
  rootNodeId?: string;
  depth?: number;
  limit?: number;
  enabled?: boolean;
};

export function useKnowledgeGraph(filters: GraphFilters, options: GraphOptions = {}) {
  const queryClient = useQueryClient();
  const request = {
    view: options.view ?? "relationship",
    rootNodeId: options.rootNodeId,
    depth: options.depth ?? 1,
    limit: options.limit,
  };
  const filterKey = JSON.stringify({ filters, request });
  const query = useQuery({
    queryKey: ["knowledge-graph", filters, request],
    queryFn: () => getKnowledgeGraph(filters, request),
    enabled: options.enabled ?? true,
    staleTime: GRAPH_QUERY_STALE_TIME_MS,
    gcTime: GRAPH_QUERY_GC_TIME_MS,
    refetchOnWindowFocus: false,
  });
  const [expanded, setExpanded] = useState<{ key: string; graph: KnowledgeGraph } | null>(null);
  const [expandingNodeId, setExpandingNodeId] = useState<string | null>(null);

  const graph = useMemo(() => {
    if (!query.data) return undefined;
    if (!expanded || expanded.key !== filterKey) return query.data;
    return mergeKnowledgeGraphs(query.data, expanded.graph);
  }, [expanded, filterKey, query.data]);

  const expandNode = useCallback(
    async (nodeId: string) => {
      if (request.view === "hierarchy") return undefined;
      setExpandingNodeId(nodeId);
      try {
        const incoming = await queryClient.fetchQuery({
          queryKey: ["knowledge-graph-neighbors", nodeId, 15, 1],
          queryFn: () => getNodeNeighbors(nodeId),
          staleTime: GRAPH_QUERY_STALE_TIME_MS,
          gcTime: GRAPH_QUERY_GC_TIME_MS,
        });
        setExpanded((current) => ({
          key: filterKey,
          graph:
            current?.key === filterKey
              ? mergeKnowledgeGraphs(current.graph, incoming)
              : incoming,
        }));
        return incoming;
      } finally {
        setExpandingNodeId(null);
      }
    },
    [filterKey, queryClient, request.view],
  );

  return { ...query, graph, expandNode, expandingNodeId };
}
