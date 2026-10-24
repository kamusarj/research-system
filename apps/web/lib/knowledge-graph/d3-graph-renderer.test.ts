import { describe, expect, it } from "vitest";
import {
  boardFooter,
  dimensionsChanged,
  graphFitTransform,
  isHierarchyBoard,
  relationshipFocusProjection,
} from "./d3-graph-renderer";
import { getNodeRadius } from "./d3-graph-styles";

it("keeps network glyphs compact while preserving degree emphasis", () => {
  expect(getNodeRadius("Concept", 0)).toBe(8);
  expect(getNodeRadius("Concept", 20)).toBe(15);
  expect(getNodeRadius("SystemRoot", 20)).toBe(22);
});

it("projects hover focus from bounded adjacency without scanning unrelated graph nodes", () => {
  const neighbors = Array.from({ length: 24 }, (_, index) => `neighbor:${index}`);
  const projection = relationshipFocusProjection(
    "focus",
    new Map([["focus", new Set(neighbors)]]),
    new Map([["focus", new Set(["edge:1", "edge:2"])]]),
    new Map(neighbors.map((id, index) => [id, 24 - index])),
  );

  expect(projection.neighborNodeIds).toEqual(new Set(neighbors));
  expect(projection.incidentEdgeIds).toEqual(new Set(["edge:1", "edge:2"]));
  expect(projection.labelNodeIds.size).toBe(17);
  expect(projection.labelNodeIds.has("focus")).toBe(true);
  expect(projection.labelNodeIds.has("neighbor:23")).toBe(true);
});

it("fits a very large hierarchy completely inside the unobscured viewport", () => {
  const fitted = graphFitTransform(
    { x: 100, y: -40, width: 4200, height: 5100 },
    390,
    680,
    { top: 96, right: 32, bottom: 54, left: 32 },
  );

  expect(fitted.scale).toBeLessThan(.15);
  expect(fitted.x + 100 * fitted.scale).toBeGreaterThanOrEqual(32);
  expect(fitted.x + 4300 * fitted.scale).toBeLessThanOrEqual(390 - 32);
  expect(fitted.y - 40 * fitted.scale).toBeGreaterThanOrEqual(96);
  expect(fitted.y + 5060 * fitted.scale).toBeLessThanOrEqual(680 - 54);
});

it("ignores resize noise but reacts to meaningful canvas changes", () => {
  expect(dimensionsChanged({ width: 1000, height: 700 }, { width: 1000.4, height: 699.7 })).toBe(false);
  expect(dimensionsChanged({ width: 1000, height: 700 }, { width: 998, height: 700 })).toBe(true);
});

it("treats only top-level system pillars as collapsed hierarchy boards", () => {
  expect(isHierarchyBoard({ type: "SystemPillar" })).toBe(true);
  expect(isHierarchyBoard({ type: "SystemRoot" })).toBe(false);
  expect(isHierarchyBoard({ type: "Concept" })).toBe(false);
});

describe("boardFooter", () => {
  it("invites a click only when the board has something behind it", () => {
    const labels = { board: "Board", nodes: "nodes", open: "Expand", close: "Collapse" };

    expect(boardFooter({ child_count: 33 }, false, labels)).toContain("Expand");
    // An empty board must not offer to open onto a blank canvas.
    expect(boardFooter({ child_count: 0 }, false, labels)).toBe("☷ 0 nodes");
    expect(boardFooter({ child_count: undefined }, false, labels)).toBe("☷ 0 nodes");
  });

  it("offers to collapse once the board is open", () => {
    const labels = { board: "Board", nodes: "nodes", open: "Expand", close: "Collapse" };

    expect(boardFooter({ child_count: 33 }, true, labels)).toBe("33 nodes · Collapse ↑");
  });
});
