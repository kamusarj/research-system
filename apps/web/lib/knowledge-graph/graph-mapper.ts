import type { GraphEdge, GraphNode, KnowledgeGraph, OntologyNode } from "./types";

export function mergeKnowledgeGraphs(current: KnowledgeGraph, incoming: KnowledgeGraph): KnowledgeGraph {
  const nodes = new Map<string, GraphNode>(current.nodes.map((node) => [node.id, node]));
  incoming.nodes.forEach((node) => nodes.set(node.id, { ...nodes.get(node.id), ...node }));
  const edges = new Map<string, GraphEdge>(current.edges.map((edge) => [edge.id, edge]));
  incoming.edges.forEach((edge) => edges.set(edge.id, { ...edges.get(edge.id), ...edge }));
  const available = new Set(nodes.keys());
  const safeEdges = [...edges.values()].filter(
    (edge) => edge.source !== edge.target && available.has(edge.source) && available.has(edge.target),
  );
  return {
    nodes: [...nodes.values()],
    edges: safeEdges,
    meta: {
      ...current.meta,
      node_count: nodes.size,
      edge_count: safeEdges.length,
      truncated: current.meta.truncated || incoming.meta.truncated,
    },
  };
}

export function addHierarchyBreadcrumb(
  graph: KnowledgeGraph,
  breadcrumb: OntologyNode[],
): KnowledgeGraph {
  if (breadcrumb.length === 0) return graph;
  const nodes = new Map<string, GraphNode>(graph.nodes.map((node) => [node.id, node]));
  breadcrumb.forEach((item) => {
    if (nodes.has(item.id)) return;
    nodes.set(item.id, {
      id: item.id,
      type: item.node_type,
      label: item.canonical_label,
      summary: item.description,
      confidence: 1,
      source_count: 0,
      published: item.lifecycle_status === "approved",
      degree: item.child_count + (item.primary_parent_id ? 1 : 0),
      primary_parent_id: item.primary_parent_id,
      child_count: item.child_count,
      lifecycle_status: item.lifecycle_status,
    });
  });

  const edges = new Map(graph.edges.map((edge) => [edge.id, edge]));
  breadcrumb.slice(1).forEach((item, index) => {
    const parent = breadcrumb[index];
    const existing = [...edges.values()].some(
      (edge) =>
        edge.source === parent.id &&
        edge.target === item.id &&
        (edge.type === "PARENT_OF" || edge.type === "BROADER_THAN"),
    );
    if (existing) return;
    const id = `breadcrumb:${parent.id}:${item.id}`;
    edges.set(id, {
      id,
      source: parent.id,
      target: item.id,
      type: "PARENT_OF",
      confidence: 1,
      evidence_count: 0,
      evidence: [],
    });
  });

  return {
    ...graph,
    nodes: [...nodes.values()],
    edges: [...edges.values()],
    meta: {
      ...graph.meta,
      node_count: nodes.size,
      edge_count: edges.size,
    },
  };
}
