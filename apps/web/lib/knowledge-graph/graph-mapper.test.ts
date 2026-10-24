import { expect, it } from "vitest";
import { addHierarchyBreadcrumb, mergeKnowledgeGraphs } from "./graph-mapper";
import type { KnowledgeGraph } from "./types";

const graph: KnowledgeGraph = {
  nodes: [{
    id: "node:1", type: "Concept", label: "RAG", summary: "", confidence: 1,
    source_count: 1, published: true, degree: 1,
  }],
  edges: [],
  meta: { node_count: 1, edge_count: 0, query: null, truncated: false, provider: "postgres" },
};

it("merges expanded graph data without duplicate nodes or dangling edges", () => {
  const merged = mergeKnowledgeGraphs(graph, {
    ...graph,
    nodes: [graph.nodes[0], {
      id: "node:2", type: "Technology", label: "pgvector", summary: "", confidence: 1,
      source_count: 1, published: true, degree: 1,
    }],
    edges: [
      { id: "edge:1", source: "node:1", target: "node:2", type: "USES", confidence: 1, evidence_count: 0, evidence: [] },
      { id: "edge:dangling", source: "node:1", target: "missing", type: "USES", confidence: 1, evidence_count: 0, evidence: [] },
    ],
    meta: { ...graph.meta, node_count: 2, edge_count: 2 },
  });
  expect(merged.nodes.map((node) => node.id)).toEqual(["node:1", "node:2"]);
  expect(merged.edges.map((edge) => edge.id)).toEqual(["edge:1"]);
});

it("adds missing hierarchy ancestors without duplicating the focused branch", () => {
  const branch = {
    ...graph,
    nodes: [{ ...graph.nodes[0], id: "pillar", label: "Governance", primary_parent_id: "root" }],
    edges: [],
    meta: { ...graph.meta, node_count: 1, edge_count: 0, view: "hierarchy" as const },
  };
  const merged = addHierarchyBreadcrumb(branch, [
    {
      id: "root",
      node_type: "SystemRoot",
      canonical_label: "Business AI Agents",
      normalized_key: "business-ai-agents",
      description: "System",
      child_count: 1,
      lifecycle_status: "approved",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    {
      id: "pillar",
      node_type: "SystemPillar",
      canonical_label: "Governance",
      normalized_key: "governance",
      description: "Governance",
      primary_parent_id: "root",
      child_count: 2,
      lifecycle_status: "approved",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ]);

  expect(merged.nodes.map((item) => item.id).sort()).toEqual(["pillar", "root"]);
  expect(merged.edges).toEqual([
    expect.objectContaining({ source: "root", target: "pillar", type: "PARENT_OF" }),
  ]);
});
