"use client";

import { useCallback, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getKnowledgeGraph, getNodeNeighbors } from "@/lib/knowledge-graph/graph-api";
import { mergeKnowledgeGraphs } from "@/lib/knowledge-graph/graph-mapper";
import type { GraphFilters, KnowledgeGraph } from "@/lib/knowledge-graph/types";

export const defaultGraphFilters: GraphFilters = {
  query: "",
  nodeTypes: [],
  sourceTypes: [],
  minConfidence: 0,
  dateFrom: "",
  dateTo: "",
};

export function useKnowledgeGraph(filters: GraphFilters) {
  const filterKey = JSON.stringify(filters);
  const query = useQuery({
    queryKey: ["knowledge-graph", filters],
    queryFn: () => getKnowledgeGraph(filters),
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
      setExpandingNodeId(nodeId);
      try {
        const incoming = await getNodeNeighbors(nodeId);
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
    [filterKey],
  );

  return { ...query, graph, expandNode, expandingNodeId };
}
