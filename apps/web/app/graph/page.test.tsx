import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import KnowledgeGraphPage from "./page";
import type { KnowledgeGraph } from "@/lib/knowledge-graph/types";

const mocks = vi.hoisted(() => ({
  graphState: {} as Record<string, unknown>,
}));

vi.mock("@tanstack/react-query", () => ({
  useQuery: () => ({ data: { nodes: 1, edges: 0, clusters: 1, by_type: { Concept: 1 } } }),
}));

vi.mock("@/hooks/use-knowledge-graph", async () => {
  const actual = await vi.importActual<typeof import("@/hooks/use-knowledge-graph")>(
    "@/hooks/use-knowledge-graph",
  );
  return { ...actual, useKnowledgeGraph: () => mocks.graphState };
});

vi.mock("@/components/knowledge-graph/graph-canvas", () => ({
  GraphCanvas: ({ onNodeSelect }: { onNodeSelect: (node: KnowledgeGraph["nodes"][number]) => void }) => (
    <button
      data-testid="mock-node"
      onClick={() => onNodeSelect({
        id: "concept:rag",
        type: "Concept",
        label: "RAG",
        summary: "Retrieval augmented generation",
        confidence: 0.9,
        source_count: 2,
        published: true,
        degree: 1,
      })}
    >
      RAG node
    </button>
  ),
}));

const baseGraph: KnowledgeGraph = {
  nodes: [{
    id: "concept:rag",
    type: "Concept",
    label: "RAG",
    summary: "Retrieval augmented generation",
    confidence: 0.9,
    source_count: 2,
    published: true,
    degree: 1,
  }],
  edges: [],
  meta: { node_count: 1, edge_count: 0, query: null, truncated: false, provider: "postgres" },
};

describe("KnowledgeGraphPage", () => {
  beforeEach(() => {
    mocks.graphState = {
      graph: baseGraph,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      expandNode: vi.fn().mockResolvedValue(baseGraph),
      expandingNodeId: null,
    };
  });

  it("renders the empty state", () => {
    mocks.graphState = {
      ...mocks.graphState,
      graph: { ...baseGraph, nodes: [], meta: { ...baseGraph.meta, node_count: 0 } },
    };
    render(<KnowledgeGraphPage />);
    expect(screen.getByText("graphEmpty")).toBeInTheDocument();
  });

  it("renders an actionable error state", () => {
    mocks.graphState = { ...mocks.graphState, graph: undefined, error: new Error("offline") };
    render(<KnowledgeGraphPage />);
    expect(screen.getByText("graphLoadFailed")).toBeInTheDocument();
    expect(screen.getByText("offline")).toBeInTheDocument();
  });

  it("opens node details when a node is selected", () => {
    render(<KnowledgeGraphPage />);
    fireEvent.click(screen.getByTestId("mock-node"));
    expect(screen.getByTestId("node-details")).toHaveTextContent("RAG");
  });
});
