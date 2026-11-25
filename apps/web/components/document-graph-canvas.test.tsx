import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

it("moves a node with a smooth pointer drag and swallows the click after the drag", async () => {
  const onSelect = vi.fn();
  render(
    <DocumentGraphCanvas graph={graph} selectedId={null} onSelect={onSelect} />,
  );

  const node = screen.getByRole("button", { name: "Human approval improves reliability" });
  const before = node.getAttribute("transform");

  fireEvent.pointerDown(node, { button: 0, pointerId: 1, clientX: 100, clientY: 100 });
  fireEvent.pointerMove(node, { pointerId: 1, clientX: 180, clientY: 150 });
  await waitFor(() => expect(node.getAttribute("transform")).not.toBe(before));
  expect(node.getAttribute("transform")).not.toBe(before);

  fireEvent.pointerUp(node, { pointerId: 1 });
  fireEvent.click(node);
  expect(onSelect).not.toHaveBeenCalled();

  fireEvent.click(node);
  expect(onSelect).toHaveBeenCalledWith(graph.nodes[1]);
});

it("allows a new drag after a graph refresh removes the grabbed node", async () => {
  const onSelect = vi.fn();
  const { rerender } = render(<DocumentGraphCanvas graph={graph} selectedId={null} onSelect={onSelect} />);
  const original = screen.getByRole("button", { name: graph.nodes[1].label });
  fireEvent.pointerDown(original, { button: 0, pointerId: 1, clientX: 100, clientY: 100 });
  fireEvent.pointerMove(original, { pointerId: 1, clientX: 140, clientY: 130 });

  const newClaim = { ...graph.nodes[1], id: "new-claim", label: "Updated claim" };
  rerender(<DocumentGraphCanvas graph={{ ...graph, nodes: [graph.nodes[0], newClaim] }} selectedId={null} onSelect={onSelect} />);

  const replacement = screen.getByRole("button", { name: newClaim.label });
  const before = replacement.getAttribute("transform");
  fireEvent.pointerDown(replacement, { button: 0, pointerId: 2, clientX: 100, clientY: 100 });
  fireEvent.pointerMove(replacement, { pointerId: 2, clientX: 180, clientY: 150 });
  await waitFor(() => expect(replacement.getAttribute("transform")).not.toBe(before));
  fireEvent.pointerUp(replacement, { pointerId: 2 });

  expect(fireEvent.keyDown(replacement, { key: " " })).toBe(false);
  expect(onSelect).toHaveBeenCalledWith(newClaim);
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

  const children = screen.getAllByRole("button", { name: /Grounded business claim/ });
  const transforms = children.map((node) => node.getAttribute("transform"));
  const yPositions = transforms.map((transform) => transform?.match(/, ([\d.]+)\)/)?.[1]);

  expect(new Set(transforms).size).toBe(12);
  expect(new Set(yPositions).size).toBe(3);
  expect(screen.getByRole("img", { name: "Đồ thị tài liệu" })).toHaveStyle({
    width: "1040px",
  });
});
