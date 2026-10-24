import { act, renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getKnowledgeGraph, getNodeNeighbors } from "@/lib/knowledge-graph/graph-api";
import {
  defaultGraphFilters,
  GRAPH_QUERY_GC_TIME_MS,
  GRAPH_QUERY_STALE_TIME_MS,
  useKnowledgeGraph,
} from "./use-knowledge-graph";

vi.mock("@/lib/knowledge-graph/graph-api", () => ({
  getKnowledgeGraph: vi.fn(),
  getNodeNeighbors: vi.fn(),
}));

const emptyGraph = {
  nodes: [],
  edges: [],
  meta: { node_count: 0, edge_count: 0, query: null, truncated: false, provider: "postgres" },
};

describe("useKnowledgeGraph cache policy", () => {
  beforeEach(() => {
    vi.mocked(getKnowledgeGraph).mockImplementation(() => new Promise(() => undefined));
    vi.mocked(getNodeNeighbors).mockResolvedValue(emptyGraph);
  });

  it("keeps graph data fresh briefly and reuses cached neighbor reads", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(
      () => useKnowledgeGraph(defaultGraphFilters, { limit: 1000 }),
      { wrapper },
    );

    await vi.waitFor(() => expect(getKnowledgeGraph).toHaveBeenCalledTimes(1));
    const query = client.getQueryCache().find({ queryKey: [
      "knowledge-graph",
      defaultGraphFilters,
      { view: "relationship", rootNodeId: undefined, depth: 1, limit: 1000 },
    ] });
    const options = query?.options as {
      staleTime?: number;
      gcTime?: number;
      refetchOnWindowFocus?: boolean;
    };
    expect(options.staleTime).toBe(GRAPH_QUERY_STALE_TIME_MS);
    expect(options.gcTime).toBe(GRAPH_QUERY_GC_TIME_MS);
    expect(options.refetchOnWindowFocus).toBe(false);

    await act(async () => {
      await result.current.expandNode("concept:rag");
      await result.current.expandNode("concept:rag");
    });
    expect(getNodeNeighbors).toHaveBeenCalledTimes(1);
  });
});
