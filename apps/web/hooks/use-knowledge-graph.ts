"use client";

import { useLayoutEffect, useMemo, useRef, useState } from "react";
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
  full?: boolean;
  enabled?: boolean;
};

type ExpansionScope = { filterKey: string; generation: number; pending: Set<string> };
type Expansion = {
  scope: ExpansionScope;
  graph?: KnowledgeGraph;
  pendingNodeIds: ReadonlySet<string>;
  error?: unknown;
};

function forScope(expansion: Expansion | null, scope: ExpansionScope): Expansion {
  return expansion?.scope === scope ? expansion : { scope, pendingNodeIds: new Set() };
}

export function useKnowledgeGraph(filters: GraphFilters, options: GraphOptions = {}) {
  const queryClient = useQueryClient();
  const request = {
    view: options.view ?? "relationship",
    rootNodeId: options.rootNodeId,
    depth: options.depth ?? 1,
    limit: options.limit,
    full: options.full,
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
  const [expansion, setExpansion] = useState<Expansion | null>(null);
  const [resetGeneration, setResetGeneration] = useState(0);
  // A fresh scope is required even when switching away and back with identical filters.
  const scope = useMemo<ExpansionScope>(() => ({
    filterKey,
    generation: resetGeneration,
    pending: new Set(),
  }), [filterKey, resetGeneration]);
  const activeScope = useRef<ExpansionScope | null>(null);

  useLayoutEffect(() => {
    activeScope.current = scope;
    return () => {
      activeScope.current = null;
    };
  }, [scope]);

  const currentExpansion = forScope(expansion, scope);
  const graph = useMemo(() => {
    if (!query.data) return undefined;
    if (!currentExpansion.graph) return query.data;
    return mergeKnowledgeGraphs(query.data, currentExpansion.graph);
  }, [currentExpansion.graph, query.data]);

  async function expandNode(nodeId: string) {
    if (request.view === "hierarchy" || activeScope.current !== scope || scope.pending.has(nodeId)) return;
    scope.pending.add(nodeId);
    const pendingNodeIds = new Set(scope.pending);
    setExpansion((current) => ({ ...forScope(current, scope), pendingNodeIds, error: undefined }));
    try {
      const incoming = await queryClient.fetchQuery({
        queryKey: ["knowledge-graph-neighbors", nodeId, filters],
        queryFn: () => getNodeNeighbors(nodeId, 15, 1, filters),
        staleTime: GRAPH_QUERY_STALE_TIME_MS,
        gcTime: GRAPH_QUERY_GC_TIME_MS,
      });
      if (activeScope.current !== scope) return;
      setExpansion((current) => {
        const expanded = forScope(current, scope);
        return {
          ...expanded,
          graph: expanded.graph ? mergeKnowledgeGraphs(expanded.graph, incoming) : incoming,
        };
      });
      return incoming;
    } catch (error) {
      if (activeScope.current === scope) {
        setExpansion((current) => ({ ...forScope(current, scope), error }));
      }
    } finally {
      scope.pending.delete(nodeId);
      const remaining = new Set(scope.pending);
      if (activeScope.current === scope) {
        setExpansion((current) => ({ ...forScope(current, scope), pendingNodeIds: remaining }));
      }
    }
  }

  function resetExpansion() {
    activeScope.current = null;
    setExpansion(null);
    setResetGeneration((value) => value + 1);
  }

  return {
    ...query,
    graph,
    expandNode,
    resetExpansion,
    expandingNodeIds: currentExpansion.pendingNodeIds,
    expansionError: currentExpansion.error,
  };
}
