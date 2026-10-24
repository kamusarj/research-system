import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { DocumentGraphCanvas } from "./document-graph-canvas";
import type { DocumentGraph } from "@/lib/types";

const graph: DocumentGraph = {
  workspace_id: "workspace-1",
  nodes: [
    {
      id: "document",
      node_type: "document",
      label: "Governed agents",
      summary: "Source",
      parent_node_id: null,
      confidence: 1,
      evidence_status: "supported",
      evidence: [],
    },
    {
      id: "claim",
      node_type: "claim",
      label: "Human approval improves reliability",
      summary: "Claim",
      parent_node_id: "document",
      confidence: 0.9,
      evidence_status: "supported",
      evidence: [],
    },
  ],
  edges: [],
  meta: { node_count: 2, edge_count: 0 },
};

it("renders the document hierarchy and selects a node", () => {
  const onSelect = vi.fn();
  render(
    <DocumentGraphCanvas graph={graph} selectedId={null} onSelect={onSelect} />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Human approval improves reliability" }));

  expect(screen.getByTestId("document-graph-canvas")).toBeInTheDocument();
  expect(onSelect).toHaveBeenCalledWith(graph.nodes[1]);
});

it("wraps dense hierarchy layers into readable rows", () => {
  const denseGraph: DocumentGraph = {
    ...graph,
    nodes: [
      graph.nodes[0],
      ...Array.from({ length: 12 }, (_, index) => ({
        ...graph.nodes[1],
        id: `claim-${index}`,
        label: `Grounded business claim ${index}`,
      })),
    ],
    meta: { node_count: 13, edge_count: 0 },
  };

  render(
    <DocumentGraphCanvas graph={denseGraph} selectedId={null} onSelect={vi.fn()} />,
  );

  const children = screen.getAllByRole("button").slice(1);
  const transforms = children.map((node) => node.getAttribute("transform"));
  const yPositions = transforms.map((transform) => transform?.match(/, ([\d.]+)\)/)?.[1]);

  expect(new Set(transforms).size).toBe(12);
  expect(new Set(yPositions).size).toBe(3);
  expect(screen.getByRole("img", { name: "Đồ thị tài liệu" })).toHaveStyle({
    width: "1040px",
  });
});
