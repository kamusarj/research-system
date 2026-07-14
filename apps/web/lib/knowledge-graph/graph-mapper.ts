import type { GraphEdge, GraphNode, KnowledgeGraph } from "./types";

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
