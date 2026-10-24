import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import KnowledgeGraphPage from "./page";
import { LocaleProvider } from "@/lib/i18n";
import type { KnowledgeGraph } from "@/lib/knowledge-graph/types";

const mocks = vi.hoisted(() => ({
  graphState: {} as Record<string, unknown>,
  expandedGraphState: {} as Record<string, unknown>,
  graphOptions: {} as Record<string, Record<string, unknown>>,
}));

vi.mock("@tanstack/react-query", () => ({
  useQuery: ({ queryKey }: { queryKey: string[] }) => {
    const common = { isLoading: false, error: null, refetch: vi.fn() };
    const ontologyNode = (id: string, label: string, childCount: number) => ({
      id,
      node_type: id === "system-root" ? "SystemRoot" : "Concept",
      canonical_label: label,
      normalized_key: label.toLowerCase().replace(/\s+/g, "-"),
      description: "System",
      child_count: childCount,
      lifecycle_status: "approved",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });
    const root = ontologyNode("system-root", "Business AI Agents", 11);
    if (queryKey[0] === "ontology-roots") return { ...common, data: [root] };
    if (queryKey[0] === "ontology-breadcrumb") {
      // A real breadcrumb names every ancestor down to the focused node.
      const focused = queryKey[1];
      return {
        ...common,
        data: focused === "system-root" || !focused
          ? [root]
          : [root, ontologyNode(String(focused), "RAG", 4)],
      };
    }
    if (queryKey[0] === "ontology-children") return { ...common, data: [] };
    if (queryKey[0] === "ontology-search") {
      return {
        ...common,
        data: [ontologyNode("deep-node", "Vector memory", 2)],
      };
    }
    return { ...common, data: { nodes: 1, edges: 0, clusters: 1, by_type: { Concept: 1 } } };
  },
}));

vi.mock("@/hooks/use-knowledge-graph", async () => {
  const actual = await vi.importActual<typeof import("@/hooks/use-knowledge-graph")>(
    "@/hooks/use-knowledge-graph",
  );
  return {
    ...actual,
    useKnowledgeGraph: (_filters: unknown, options: Record<string, unknown>) => {
      mocks.graphOptions.filters = _filters as Record<string, unknown>;
      // The expanded-board query is the only hierarchy query bounded to 40 nodes; the
      // overview query draws the current focus and its direct children.
      const key = options.view === "relationship"
        ? "relationship"
        : options.limit === 40
          ? "expanded"
          : "overview";
      mocks.graphOptions[key] = options;
      return key === "expanded" ? mocks.expandedGraphState : mocks.graphState;
    },
  };
});

vi.mock("@/components/knowledge-graph/d3-graph-canvas-lazy", () => ({
  D3GraphCanvas: ({
    onNodeSelect,
    onExpandNode,
    layout,
    status,
  }: {
    onNodeSelect: (node: KnowledgeGraph["nodes"][number]) => void;
    onExpandNode: (nodeId: string) => void;
    layout: string;
    status?: { detail: string };
  }) => (
    <div>
      <span data-testid="mock-view">{layout}</span>
      <span data-testid="mock-status">{status?.detail}</span>
      <button data-testid="mock-board" onClick={() => onExpandNode("pillar")}>
        Agent System Architecture board
      </button>
      <button data-testid="mock-deep-node" onClick={() => onExpandNode("concept:rag")}>
        RAG branch
      </button>
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
    </div>
  ),
}));

const baseGraph: KnowledgeGraph = {
  nodes: [
    {
      id: "system-root",
      type: "SystemRoot",
      label: "Business AI Agents",
      summary: "System",
      confidence: 1,
      source_count: 0,
      published: true,
      degree: 1,
      child_count: 1,
    },
    {
      id: "pillar",
      type: "SystemPillar",
      label: "Agent System Architecture",
      summary: "Agent architecture",
      confidence: 1,
      source_count: 0,
      published: true,
      degree: 1,
      primary_parent_id: "system-root",
      child_count: 1,
    },
  ],
  edges: [{
    id: "root-pillar",
    source: "system-root",
    target: "pillar",
    type: "PARENT_OF",
    confidence: 1,
    evidence_count: 0,
    evidence: [],
  }],
  meta: { node_count: 2, edge_count: 1, query: null, truncated: false, provider: "postgres" },
};

const expandedGraph: KnowledgeGraph = {
  nodes: [
    baseGraph.nodes[1],
    {
      id: "concept:rag",
      type: "Concept",
      label: "RAG",
      summary: "Retrieval augmented generation",
      confidence: 0.9,
      source_count: 2,
      published: true,
      degree: 1,
      primary_parent_id: "pillar",
    },
  ],
  edges: [{
    id: "pillar-rag",
    source: "pillar",
    target: "concept:rag",
    type: "PARENT_OF",
    confidence: 1,
    evidence_count: 0,
    evidence: [],
  }],
  meta: { node_count: 2, edge_count: 1, query: null, truncated: false, provider: "postgres" },
};

/** Render with real copy, for assertions about what a reader actually sees. */
function renderTranslated() {
  return render(
    <LocaleProvider>
      <KnowledgeGraphPage />
    </LocaleProvider>,
  );
}

describe("KnowledgeGraphPage", () => {
  beforeEach(() => {
    mocks.graphOptions = {};
    mocks.graphState = {
      graph: baseGraph,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      expandNode: vi.fn().mockResolvedValue(baseGraph),
      expandingNodeId: null,
    };
    mocks.expandedGraphState = {
      graph: expandedGraph,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      expandNode: vi.fn(),
      expandingNodeId: null,
    };
  });

  it("renders the empty state", () => {
    mocks.graphState = {
      ...mocks.graphState,
      graph: { ...baseGraph, nodes: [], meta: { ...baseGraph.meta, node_count: 0 } },
    };
    render(<KnowledgeGraphPage />);
    fireEvent.click(screen.getByRole("button", { name: "relationshipView" }));
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

  it("opens in hierarchy mode and keeps the selection when switching to relationships", () => {
    render(<KnowledgeGraphPage />);
    expect(screen.getByTestId("mock-view")).toHaveTextContent("hierarchy");
    fireEvent.click(screen.getByTestId("mock-node"));
    fireEvent.click(screen.getByRole("button", { name: "relationshipView" }));

    expect(screen.getByTestId("mock-view")).toHaveTextContent("relationship");
    expect(screen.getByTestId("node-details")).toHaveTextContent("RAG");
  });

  it("offers the GitNexus-style network, hierarchy and orbit layouts", () => {
    renderTranslated();

    expect(screen.getByRole("button", { name: "Phân cấp" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Quỹ đạo" }));
    expect(screen.getByTestId("mock-view")).toHaveTextContent("orbit");
    expect(mocks.graphOptions.relationship).toMatchObject({ view: "relationship", limit: 1000 });
    fireEvent.click(screen.getByRole("button", { name: "Mạng" }));
    expect(screen.getByTestId("mock-view")).toHaveTextContent("relationship");
  });

  it("loads the complete synchronized hierarchy and can focus a branch", () => {
    render(<KnowledgeGraphPage />);

    expect(mocks.graphOptions.overview).toMatchObject({
      rootNodeId: undefined,
      depth: 1,
      limit: 1000,
    });
    expect(screen.getByRole("link", { name: "openSystemMap" })).toHaveAttribute(
      "href",
      "/graph/system",
    );

    fireEvent.click(screen.getByTestId("mock-board"));

    expect(mocks.graphOptions.overview).toMatchObject({
      rootNodeId: "pillar",
      depth: 1,
      limit: 1000,
    });
  });

  it("drills into a node that is not a pillar, so a deep branch is not a dead end", () => {
    mocks.graphState = {
      ...mocks.graphState,
      graph: {
        ...expandedGraph,
        nodes: expandedGraph.nodes.map((node) =>
          node.id === "concept:rag" ? { ...node, child_count: 4 } : node,
        ),
      },
    };
    render(<KnowledgeGraphPage />);

    fireEvent.click(screen.getByTestId("mock-deep-node"));

    // The view is redrawn around the concept itself rather than refusing to open it.
    expect(mocks.graphOptions.overview).toMatchObject({ rootNodeId: "concept:rag", depth: 1 });
  });

  it("leaves a leaf node alone instead of drilling into nothing", () => {
    mocks.graphState = { ...mocks.graphState, graph: expandedGraph };
    render(<KnowledgeGraphPage />);

    fireEvent.click(screen.getByTestId("mock-deep-node"));

    expect(mocks.graphOptions.overview).toMatchObject({ rootNodeId: undefined });
  });

  it("keeps the Business AI Agents ontology on a separate route", () => {
    render(<KnowledgeGraphPage />);
    expect(screen.getByRole("link", { name: "openSystemMap" })).toHaveAttribute(
      "href",
      "/graph/system",
    );
  });

  it("returns the hierarchy to the root when the view is reset", () => {
    mocks.graphState = {
      ...mocks.graphState,
      graph: {
        ...expandedGraph,
        nodes: expandedGraph.nodes.map((node) =>
          node.id === "concept:rag" ? { ...node, child_count: 4 } : node,
        ),
      },
    };
    render(<KnowledgeGraphPage />);
    fireEvent.click(screen.getByTestId("mock-deep-node"));

    fireEvent.click(screen.getByRole("button", { name: "reset" }));

    expect(mocks.graphOptions.overview).toMatchObject({ rootNodeId: undefined });
  });

  it("says how much of the graph is hidden instead of only that something was", () => {
    mocks.graphState = {
      ...mocks.graphState,
      graph: {
        ...baseGraph,
        meta: {
          ...baseGraph.meta,
          truncated: true,
          total_node_count: 132,
          total_edge_count: 210,
          node_limit: 60,
        },
      },
    };
    renderTranslated();

    expect(screen.getByText(/Đang hiển thị 2 trong 132 nút/)).toBeInTheDocument();
    expect(screen.getByText(/giới hạn vận hành an toàn là 1.000 nút/)).toBeInTheDocument();
  });

  it("requests up to 1,000 nodes in both relationship and hierarchy layouts", () => {
    renderTranslated();
    expect(mocks.graphOptions.overview).toMatchObject({ limit: 1000, view: "hierarchy" });

    fireEvent.click(screen.getByRole("button", { name: /Mạng/ }));

    expect(mocks.graphOptions.relationship).toMatchObject({ limit: 1000, view: "relationship" });
  });

  it("counts what is drawn, and names the wider total separately", () => {
    mocks.graphState = {
      ...mocks.graphState,
      graph: { ...baseGraph, meta: { ...baseGraph.meta, total_node_count: 132 } },
    };
    renderTranslated();

    const metrics = document.querySelector(".metric-row");
    // Two nodes are on the canvas; the header must not claim the whole graph is visible.
    expect(metrics?.textContent).toContain("2");
    expect(metrics?.textContent).toContain("/ 132");
  });

  it("keeps unplaced knowledge out of the canvas and reports it without a verbose banner", () => {
    mocks.graphState = {
      ...mocks.graphState,
      graph: {
        ...baseGraph,
        nodes: [
          ...baseGraph.nodes,
          {
            ...baseGraph.nodes[1],
            id: "unplaced",
            label: "Unplaced concept",
            primary_parent_id: undefined,
            child_count: 0,
          },
        ],
        meta: { ...baseGraph.meta, node_count: 3, total_node_count: 3 },
      },
    };
    renderTranslated();

    expect(screen.getByTestId("mock-status")).toHaveTextContent("1 chưa xếp");
    expect(document.querySelector(".graph-structure-note")).not.toBeInTheDocument();
    expect(document.querySelector(".metric-row")?.textContent).toContain("quan hệ ngữ nghĩa");
  });

  it("keeps the explorer rail optional so the graph owns the primary width", () => {
    renderTranslated();

    const workspace = document.querySelector(".graph-workspace");
    expect(workspace).toHaveClass("explorer-closed");
    fireEvent.click(screen.getByRole("button", { name: "Khám phá" }));
    expect(workspace).toHaveClass("explorer-open");
  });

  it("explains an empty branch instead of drawing a blank canvas", () => {
    const focused = { ...expandedGraph.nodes[1], child_count: 1 };
    mocks.graphState = {
      ...mocks.graphState,
      graph: {
        ...baseGraph,
        nodes: [focused],
        edges: [],
        meta: { ...baseGraph.meta, node_count: 1, edge_count: 0 },
      },
    };
    renderTranslated();
    fireEvent.click(screen.getByTestId("mock-deep-node"));

    expect(screen.getByTestId("empty-branch")).toBeInTheDocument();
    expect(screen.getByText(/chưa có tri thức được duyệt/i)).toBeInTheDocument();
  });

  it("does not claim a populated branch is empty", () => {
    renderTranslated();

    expect(screen.queryByTestId("empty-branch")).not.toBeInTheDocument();
  });

  it("sends hierarchy search through the shared knowledge graph query", () => {
    renderTranslated();

    fireEvent.change(screen.getByPlaceholderText("Tìm nút…"), {
      target: { value: "vector" },
    });

    expect(mocks.graphOptions.filters).toMatchObject({ query: "vector" });
  });

  it("announces the current selection for a screen reader", () => {
    renderTranslated();

    fireEvent.click(screen.getByTestId("mock-node"));

    expect(screen.getByRole("status")).toHaveTextContent("Đã chọn Khái niệm: RAG");
  });
});
