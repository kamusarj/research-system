import { describe, expect, it } from "vitest";
import {
  buildGraphPresentation,
  buildSystemMapPresentation,
  collapseDenseHierarchyLeaves,
  graphClusterCount,
  mergeHierarchyRelationshipOverlay,
  rankRelationshipLabels,
  relationshipLabelBudget,
} from "./graph-visualization";
import type { GraphNode, KnowledgeGraph } from "./types";

const node = (id: string, degree = 0, type = "Concept"): GraphNode => ({
  id,
  type,
  label: id,
  summary: "",
  confidence: 1,
  source_count: 1,
  published: true,
  degree,
});

const graph: KnowledgeGraph = {
  nodes: [node("root", 1), node("child", 1), node("unplaced", 8)],
  edges: [{
    id: "root-child",
    source: "root",
    target: "child",
    type: "PARENT_OF",
    confidence: 1,
    evidence_count: 0,
    evidence: [],
  }],
  meta: { node_count: 3, edge_count: 1, query: null, truncated: false, provider: "postgres" },
};

describe("buildGraphPresentation", () => {
  it("removes unplaced roots from the hierarchy overview and reports them", () => {
    const result = buildGraphPresentation(graph, "hierarchy", false);

    expect(result.graph.nodes.map((item) => item.id)).toEqual(["root", "child"]);
    expect(result.graph.edges).toHaveLength(1);
    expect(result.unplacedNodeCount).toBe(1);
  });

  it("preserves every node in relationship and focused hierarchy views", () => {
    expect(buildGraphPresentation(graph, "relationship", false).graph.nodes).toHaveLength(3);
    expect(buildGraphPresentation(graph, "hierarchy", true).graph.nodes).toHaveLength(3);
  });
});

describe("graphClusterCount", () => {
  it("counts connected components without another API projection", () => {
    const disconnected: KnowledgeGraph = {
      ...graph,
      nodes: [...graph.nodes, node("isolated")],
    };

    expect(graphClusterCount(disconnected)).toBe(3);
    expect(graphClusterCount({ ...graph, nodes: [], edges: [] })).toBe(0);
  });
});

describe("system map folding projection", () => {
  const systemGraph: KnowledgeGraph = {
    nodes: [
      { ...node("system", 2, "SystemRoot"), child_count: 2 },
      { ...node("pillar-a", 2, "SystemPillar"), primary_parent_id: "system", child_count: 1 },
      { ...node("pillar-b", 1, "SystemPillar"), primary_parent_id: "system", child_count: 0 },
      { ...node("concept-a", 1), primary_parent_id: "pillar-a" },
    ],
    edges: [
      { ...graph.edges[0], id: "system-a", source: "system", target: "pillar-a" },
      { ...graph.edges[0], id: "system-b", source: "system", target: "pillar-b" },
      { ...graph.edges[0], id: "a-concept", source: "pillar-a", target: "concept-a" },
    ],
    meta: { ...graph.meta, node_count: 4, edge_count: 3, provider: "postgres-system" },
  };

  it("starts with only the system root and collapsed top-level pillars", () => {
    const result = buildSystemMapPresentation(systemGraph, null);

    expect(result.nodes.map((item) => item.id)).toEqual(["system", "pillar-a", "pillar-b"]);
    expect(result.edges.map((edge) => edge.id)).toEqual(["system-a", "system-b"]);
    expect(result.nodes.filter((item) => item.expanded_group)).toHaveLength(0);
    expect(result.meta).toMatchObject({ node_count: 3, edge_count: 2 });
  });

  it("adds only the opened pillar's direct children and marks its compound board", () => {
    const result = buildSystemMapPresentation(systemGraph, "pillar-a");

    expect(result.nodes.map((item) => item.id)).toEqual(["system", "pillar-a", "pillar-b", "concept-a"]);
    expect(result.nodes.find((item) => item.id === "pillar-a")?.expanded_group).toBe(true);
    expect(result.nodes.find((item) => item.id === "pillar-b")?.expanded_group).toBe(false);
    expect(result.edges.map((edge) => edge.id)).toEqual(["system-a", "system-b", "a-concept"]);
  });
});

describe("semantic label priority", () => {
  it("ranks connected research anchors ahead of low-value labels", () => {
    const ranks = rankRelationshipLabels([
      node("leaf", 0),
      node("hub", 12),
      node("research", 3, "ResearchItem"),
    ]);

    expect(ranks.get("hub")).toBe(0);
    expect(ranks.get("leaf")).toBe(2);
  });

  it("reveals progressively more labels as the reader zooms in", () => {
    expect(relationshipLabelBudget(429, 0.4)).toBeLessThan(
      relationshipLabelBudget(429, 1),
    );
    expect(relationshipLabelBudget(429, 2.5)).toBe(429);
  });
});

describe("progressive hierarchy boards", () => {
  const denseGraph = (): KnowledgeGraph => {
    const leaves = Array.from({ length: 12 }, (_, index) => node(`leaf-${index}`, index));
    return {
      nodes: [{ ...node("parent", 12), child_count: 12 }, ...leaves],
      edges: leaves.map((leaf, index) => ({
        id: `parent-${index}`,
        source: "parent",
        target: leaf.id,
        type: "PARENT_OF",
        confidence: 1,
        evidence_count: 0,
        evidence: [],
      })),
      meta: { node_count: 13, edge_count: 12, query: null, truncated: false, provider: "postgres" },
    };
  };

  it("previews a bounded leaf set and records the hidden count on its parent", () => {
    const result = collapseDenseHierarchyLeaves(denseGraph(), new Set(), 8, 4);

    expect(result.graph.nodes).toHaveLength(5);
    expect(result.hiddenLeafCount).toBe(8);
    expect(result.collapsedParentCount).toBe(1);
    expect(result.graph.nodes.find((item) => item.id === "parent")).toMatchObject({
      collapsed_leaf_count: 8,
      leaf_group_expanded: false,
    });
  });

  it("restores every loaded leaf when its parent is expanded", () => {
    const result = collapseDenseHierarchyLeaves(denseGraph(), new Set(["parent"]), 8, 4);

    expect(result.graph.nodes).toHaveLength(13);
    expect(result.hiddenLeafCount).toBe(0);
    expect(result.graph.nodes.find((item) => item.id === "parent")).toMatchObject({
      collapsed_leaf_count: 0,
      leaf_group_expanded: true,
    });
  });
});

describe("hierarchy relationship overlay", () => {
  it("adds accepted semantic edges only when both hierarchy cards are visible", () => {
    const relationship: KnowledgeGraph = {
      ...graph,
      edges: [
        { ...graph.edges[0], id: "semantic-visible", type: "RELATED_TO" },
        { ...graph.edges[0], id: "semantic-hidden", source: "root", target: "unplaced", type: "USES_TECH" },
      ],
    };
    const hierarchy = buildGraphPresentation(graph, "hierarchy", false).graph;
    const result = mergeHierarchyRelationshipOverlay(hierarchy, relationship);

    expect(result.semanticEdgeCount).toBe(1);
    expect(result.graph.edges.map((edge) => edge.id)).toEqual(["root-child", "semantic-visible"]);
  });
});
