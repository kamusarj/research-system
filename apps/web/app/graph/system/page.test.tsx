import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import SystemKnowledgeMapPage from "./page";

const systemGraph = {
  nodes: [
    {
      id: "system-root", type: "SystemRoot", label: "Business AI Agents",
      summary: "Canonical system architecture", confidence: 1, source_count: 0,
      published: true, degree: 1, child_count: 1,
    },
    {
      id: "pillar", type: "SystemPillar", label: "Agent Architecture",
      summary: "System pillar", confidence: 1, source_count: 0,
      published: true, degree: 2, child_count: 1, primary_parent_id: "system-root",
    },
    {
      id: "concept", type: "Concept", label: "Orchestration",
      summary: "System concept", confidence: 1, source_count: 0,
      published: true, degree: 1, child_count: 0, primary_parent_id: "pillar",
    },
  ],
  edges: [
    {
      id: "root-pillar", source: "system-root", target: "pillar", type: "PARENT_OF",
      confidence: 1, evidence_count: 0, evidence: [],
    },
    {
      id: "pillar-concept", source: "pillar", target: "concept", type: "PARENT_OF",
      confidence: 1, evidence_count: 0, evidence: [],
    },
  ],
  meta: { node_count: 3, edge_count: 2, query: null, truncated: false, provider: "postgres-system" },
};

vi.mock("@tanstack/react-query", () => ({
  useQuery: ({ queryKey }: { queryKey: string[] }) => {
    if (queryKey[0] === "business-ai-agents-system-map") {
      return { data: systemGraph, isLoading: false, error: null };
    }
    return { data: [], isLoading: false, error: null };
  },
}));

vi.mock("@/components/knowledge-graph/d3-graph-canvas", () => ({
  D3GraphCanvas: ({
    nodes,
    layout,
    labelsVisible,
    onNodeSelect,
    onExpandNode,
  }: {
    nodes: typeof systemGraph.nodes;
    layout: string;
    labelsVisible: boolean;
    onNodeSelect: (node: typeof systemGraph.nodes[0]) => void;
    onExpandNode: (nodeId: string) => void;
  }) => (
    <div>
      <span data-testid="visible-system-nodes">{nodes.map((node) => node.id).join(",")}</span>
      <span data-testid="system-layout">{layout}</span>
      <span data-testid="system-labels">{String(labelsVisible)}</span>
      <button onClick={() => onNodeSelect(systemGraph.nodes[0])}>Business AI Agents node</button>
      <button onClick={() => onExpandNode("pillar")}>Toggle Agent Architecture</button>
    </div>
  ),
}));

it("renders the Business AI Agents system graph on its own route", () => {
  render(<SystemKnowledgeMapPage />);

  expect(screen.getByRole("link", { name: /backToKnowledgeGraph/ })).toHaveAttribute(
    "href",
    "/graph",
  );
  expect(screen.getByText("systemKnowledgeMap")).toBeInTheDocument();
  expect(screen.queryByText("graphProjection")).not.toBeInTheDocument();
  expect(screen.queryByText("systemMapIntro")).not.toBeInTheDocument();
  expect(document.querySelector(".graph-studio.system-map-studio")).toBeInTheDocument();
  expect(screen.queryByTestId("node-details")).not.toBeInTheDocument();
  expect(screen.getByRole("textbox", { name: "findNode" })).toBeInTheDocument();
  expect(screen.getByTestId("system-layout")).toHaveTextContent("hierarchy");
  expect(screen.getByTestId("visible-system-nodes")).toHaveTextContent("system-root,pillar");
  expect(screen.getByTestId("visible-system-nodes")).not.toHaveTextContent("concept");
  fireEvent.click(screen.getByRole("button", { name: "Toggle Agent Architecture" }));
  expect(screen.getByTestId("visible-system-nodes")).toHaveTextContent("system-root,pillar,concept");
  fireEvent.click(screen.getByRole("button", { name: "Toggle Agent Architecture" }));
  expect(screen.getByTestId("visible-system-nodes")).toHaveTextContent("system-root,pillar");
  fireEvent.click(screen.getByRole("button", { name: "Business AI Agents node" }));
  expect(screen.getByTestId("node-details")).toHaveTextContent("Business AI Agents");
  fireEvent.click(screen.getByRole("button", { name: "relationshipView" }));
  expect(screen.getByTestId("system-layout")).toHaveTextContent("relationship");
  expect(screen.getByTestId("visible-system-nodes")).toHaveTextContent("system-root,pillar,concept");
  fireEvent.click(screen.getByRole("button", { name: "graphLabels" }));
  expect(screen.getByTestId("system-labels")).toHaveTextContent("false");
  fireEvent.click(screen.getByRole("button", { name: "reset" }));
  expect(screen.getByTestId("system-layout")).toHaveTextContent("hierarchy");
  expect(screen.getByTestId("system-labels")).toHaveTextContent("true");
});
