import { expect, it } from "vitest";
import { buildHierarchyLayout } from "./hierarchy-layout";
import type { GraphEdge, GraphNode } from "./types";

const node = (id: string, label: string): GraphNode => ({
  id,
  type: "SystemPillar",
  label,
  summary: "",
  confidence: 1,
  source_count: 0,
  published: true,
  degree: 1,
});

it("places hierarchy children to the right of their parent in stable label order", () => {
  const nodes = [node("root", "Root"), node("b", "Beta"), node("a", "Alpha")];
  const edges: GraphEdge[] = [
    { id: "1", source: "root", target: "b", type: "PARENT_OF", confidence: 1, evidence_count: 0, evidence: [] },
    { id: "2", source: "root", target: "a", type: "PARENT_OF", confidence: 1, evidence_count: 0, evidence: [] },
  ];

  const positions = buildHierarchyLayout(nodes, edges, 800, 500);

  expect(positions.get("root")?.depth).toBe(0);
  expect(positions.get("a")?.depth).toBe(1);
  expect(positions.get("a")!.x).toBeGreaterThan(positions.get("root")!.x);
  expect(positions.get("a")!.y).toBeLessThan(positions.get("b")!.y);
  expect(positions.get("root")!.y).toBe(
    (positions.get("a")!.y + positions.get("b")!.y) / 2,
  );
});

it("contains a large opened board node list inside the expanded board boundary", () => {
  const root = node("root", "Root");
  root.type = "SystemRoot";
  const board = node("board", "Data Board");
  board.primary_parent_id = root.id;
  board.expanded_group = true;
  const sibling = node("sibling", "Operations Board");
  sibling.primary_parent_id = root.id;
  const children = Array.from({ length: 25 }, (_, index) => {
    const item = node(`child-${index}`, `Node ${String(index).padStart(2, "0")}`);
    item.type = "Concept";
    item.primary_parent_id = board.id;
    return item;
  });
  const edges: GraphEdge[] = [
    { id: "root-board", source: root.id, target: board.id, type: "PARENT_OF", confidence: 1, evidence_count: 0, evidence: [] },
    { id: "root-sibling", source: root.id, target: sibling.id, type: "PARENT_OF", confidence: 1, evidence_count: 0, evidence: [] },
    ...children.map((item) => ({
      id: `board-${item.id}`,
      source: board.id,
      target: item.id,
      type: "PARENT_OF",
      confidence: 1,
      evidence_count: 0,
      evidence: [],
    })),
  ];

  const positions = buildHierarchyLayout([root, board, sibling, ...children], edges, 900, 680);
  const boardPosition = positions.get(board.id)!;
  const childColumns = new Set(children.map((item) => positions.get(item.id)?.x));
  const boardLeft = boardPosition.x - boardPosition.width! / 2;
  const boardRight = boardPosition.x + boardPosition.width! / 2;
  const boardTop = boardPosition.y - boardPosition.height! / 2;
  const boardBottom = boardPosition.y + boardPosition.height! / 2;

  expect(positions.get(root.id)!.x).toBeLessThan(positions.get(board.id)!.x);
  expect(boardPosition.width).toBeGreaterThan(184);
  expect(boardPosition.height).toBeGreaterThan(76);
  expect(childColumns.size).toBe(3);
  children.forEach((item) => {
    const childPosition = positions.get(item.id)!;
    expect(childPosition.x - 78).toBeGreaterThanOrEqual(boardLeft);
    expect(childPosition.x + 78).toBeLessThanOrEqual(boardRight);
    expect(childPosition.y - 24).toBeGreaterThanOrEqual(boardTop + 64);
    expect(childPosition.y + 24).toBeLessThanOrEqual(boardBottom);
  });
  expect(positions.get(sibling.id)).toBeDefined();
  expect(positions.get(sibling.id)!.x).toBeLessThan(boardLeft);
});

it("packs a large shallow forest into multiple readable branch columns", () => {
  const roots = Array.from({ length: 12 }, (_, index) => node(`root-${index}`, `Root ${index}`));
  const children = roots.map((root, index) => {
    const child = node(`child-${index}`, `Child ${index}`);
    child.type = "ResearchItem";
    child.primary_parent_id = root.id;
    return child;
  });
  const edges = roots.map((root, index) => ({
    id: `edge-${index}`,
    source: root.id,
    target: children[index].id,
    type: "PARENT_OF",
    confidence: 1,
    evidence_count: 0,
    evidence: [],
  }));

  const positions = buildHierarchyLayout([...roots, ...children], edges, 1200, 700);
  const rootColumns = new Set(roots.map((root) => positions.get(root.id)?.x));

  expect(rootColumns.size).toBe(4);
  roots.forEach((root, index) => {
    expect(positions.get(children[index].id)!.x).toBeGreaterThan(positions.get(root.id)!.x);
  });
});
