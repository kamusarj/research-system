import type { GraphNode, GraphView, KnowledgeGraph } from "./types";

const HIERARCHY_EDGE_TYPES = new Set(["PARENT_OF", "BROADER_THAN"]);

export function isHierarchyEdgeType(type: string): boolean {
  return HIERARCHY_EDGE_TYPES.has(type);
}

export function graphClusterCount(graph: KnowledgeGraph): number {
  const adjacency = new Map(graph.nodes.map((node) => [node.id, new Set<string>()]));
  graph.edges.forEach((edge) => {
    if (!adjacency.has(edge.source) || !adjacency.has(edge.target)) return;
    adjacency.get(edge.source)?.add(edge.target);
    adjacency.get(edge.target)?.add(edge.source);
  });

  const remaining = new Set(adjacency.keys());
  let clusters = 0;
  while (remaining.size > 0) {
    const root = remaining.values().next().value as string;
    remaining.delete(root);
    const queue = [root];
    while (queue.length > 0) {
      const current = queue.pop() as string;
      adjacency.get(current)?.forEach((neighbor) => {
        if (!remaining.delete(neighbor)) return;
        queue.push(neighbor);
      });
    }
    clusters += 1;
  }
  return clusters;
}

export type GraphPresentation = {
  graph: KnowledgeGraph;
  unplacedNodeCount: number;
};

/**
 * Project the canonical system ontology into its folding-board presentation.
 *
 * The API response remains complete so selection and inspection never lose context. The canvas
 * starts with the system root and its top-level pillars, then adds only the direct children of the
 * currently opened pillar. `expanded_group` is presentation state consumed by the compound-board
 * layout; it is never written back to canonical data.
 */
export function buildSystemMapPresentation(
  graph: KnowledgeGraph,
  expandedPillarId: string | null,
): KnowledgeGraph {
  const nodeById = new Map(graph.nodes.map((node) => [node.id, node]));
  const rootIds = new Set(
    graph.nodes.filter((node) => node.type === "SystemRoot").map((node) => node.id),
  );
  const hierarchyEdges = graph.edges.filter((edge) => isHierarchyEdgeType(edge.type));
  const linkedPillarIds = new Set(
    hierarchyEdges
      .filter((edge) => rootIds.has(edge.source) && nodeById.get(edge.target)?.type === "SystemPillar")
      .map((edge) => edge.target),
  );
  const pillarIds = linkedPillarIds.size > 0
    ? linkedPillarIds
    : new Set(graph.nodes.filter((node) => node.type === "SystemPillar").map((node) => node.id));
  const openedPillarId = expandedPillarId && pillarIds.has(expandedPillarId)
    ? expandedPillarId
    : null;
  const visibleIds = new Set<string>([...rootIds, ...pillarIds]);

  if (openedPillarId) {
    hierarchyEdges
      .filter((edge) => edge.source === openedPillarId)
      .forEach((edge) => visibleIds.add(edge.target));
  }

  const nodes = graph.nodes
    .filter((node) => visibleIds.has(node.id))
    .map((node) => node.type === "SystemPillar"
      ? { ...node, expanded_group: node.id === openedPillarId }
      : node);
  const edges = graph.edges.filter(
    (edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target),
  );

  return {
    ...graph,
    nodes,
    edges,
    meta: { ...graph.meta, node_count: nodes.length, edge_count: edges.length },
  };
}

/**
 * Keep the hierarchy honest and readable.
 *
 * A relationship corpus can contain hundreds of approved nodes that do not yet have a display
 * parent. Drawing each of those as a root makes fit-to-screen shrink the real hierarchy to a line.
 * They stay in the corpus and remain visible in relationship/search/focused views; the overview
 * hierarchy draws only nodes that participate in an approved parent/child edge and reports the
 * omitted count as unplaced knowledge.
 */
export function buildGraphPresentation(
  graph: KnowledgeGraph,
  view: GraphView,
  preserveUnplaced: boolean,
): GraphPresentation {
  if (view !== "hierarchy" || preserveUnplaced) {
    return { graph, unplacedNodeCount: 0 };
  }

  const hierarchyEdges = graph.edges.filter((edge) => HIERARCHY_EDGE_TYPES.has(edge.type));
  const placedIds = new Set<string>();
  hierarchyEdges.forEach((edge) => {
    placedIds.add(edge.source);
    placedIds.add(edge.target);
  });

  // A truly edgeless focused result is still useful. The caller opts into preserveUnplaced for
  // searches and focused branches, but this fallback also prevents a misleading empty canvas if a
  // provider returns a single explicit result without marking the request as focused.
  if (placedIds.size === 0 && graph.nodes.length <= 1) {
    return { graph, unplacedNodeCount: 0 };
  }

  const nodes = graph.nodes.filter((node) => placedIds.has(node.id));
  const visibleIds = new Set(nodes.map((node) => node.id));
  const edges = hierarchyEdges.filter(
    (edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target),
  );

  return {
    graph: {
      ...graph,
      nodes,
      edges,
      meta: {
        ...graph.meta,
        node_count: nodes.length,
        edge_count: edges.length,
      },
    },
    unplacedNodeCount: Math.max(0, graph.nodes.length - nodes.length),
  };
}

export type ProgressiveHierarchyPresentation = {
  graph: KnowledgeGraph;
  hiddenLeafCount: number;
  collapsedParentCount: number;
};

/**
 * Keep dense board branches scannable without changing the canonical hierarchy.
 *
 * A parent may have dozens of direct research-item leaves. Showing every leaf on first load makes
 * the hierarchy look like a spreadsheet laid sideways. The browser keeps a small, deterministic
 * preview and marks the parent with the number of hidden leaves; expanding that parent restores
 * the complete local branch from the already-loaded response.
 */
export function collapseDenseHierarchyLeaves(
  graph: KnowledgeGraph,
  expandedParentIds: ReadonlySet<string>,
  threshold = 8,
  previewCount = 4,
): ProgressiveHierarchyPresentation {
  const hierarchyEdges = graph.edges.filter((edge) => isHierarchyEdgeType(edge.type));
  const outgoing = new Set(hierarchyEdges.map((edge) => edge.source));
  const nodeById = new Map(graph.nodes.map((node) => [node.id, node]));
  const childrenByParent = new Map<string, GraphNode[]>();

  hierarchyEdges.forEach((edge) => {
    const child = nodeById.get(edge.target);
    if (!child) return;
    const children = childrenByParent.get(edge.source) ?? [];
    children.push(child);
    childrenByParent.set(edge.source, children);
  });

  const hiddenIds = new Set<string>();
  const parentState = new Map<string, { hidden: number; expanded: boolean }>();
  childrenByParent.forEach((children, parentId) => {
    const leaves = children
      .filter((child) => !outgoing.has(child.id) && (child.child_count ?? 0) === 0)
      .sort((left, right) =>
        right.degree - left.degree ||
        right.source_count - left.source_count ||
        left.label.localeCompare(right.label),
      );
    if (leaves.length <= threshold) return;
    const expanded = expandedParentIds.has(parentId);
    if (!expanded) leaves.slice(Math.max(1, previewCount)).forEach((node) => hiddenIds.add(node.id));
    parentState.set(parentId, {
      hidden: expanded ? 0 : Math.max(0, leaves.length - Math.max(1, previewCount)),
      expanded,
    });
  });

  if (parentState.size === 0) {
    return { graph, hiddenLeafCount: 0, collapsedParentCount: 0 };
  }

  const nodes = graph.nodes
    .filter((node) => !hiddenIds.has(node.id))
    .map((node) => {
      const state = parentState.get(node.id);
      if (!state) return node;
      return {
        ...node,
        collapsed_leaf_count: state.hidden,
        leaf_group_expanded: state.expanded,
      };
    });
  const visibleIds = new Set(nodes.map((node) => node.id));
  const edges = graph.edges.filter(
    (edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target),
  );

  return {
    graph: {
      ...graph,
      nodes,
      edges,
      meta: { ...graph.meta, node_count: nodes.length, edge_count: edges.length },
    },
    hiddenLeafCount: hiddenIds.size,
    collapsedParentCount: [...parentState.values()].filter((state) => state.hidden > 0).length,
  };
}

export type HierarchyRelationshipOverlay = {
  graph: KnowledgeGraph;
  semanticEdgeCount: number;
};

/** Add real accepted cross-relationships to the visible hierarchy cards only. */
export function mergeHierarchyRelationshipOverlay(
  hierarchy: KnowledgeGraph,
  relationship: KnowledgeGraph | undefined,
): HierarchyRelationshipOverlay {
  if (!relationship) return { graph: hierarchy, semanticEdgeCount: 0 };
  const visibleIds = new Set(hierarchy.nodes.map((node) => node.id));
  const existingIds = new Set(hierarchy.edges.map((edge) => edge.id));
  const semanticEdges = relationship.edges.filter(
    (edge) =>
      !isHierarchyEdgeType(edge.type) &&
      visibleIds.has(edge.source) &&
      visibleIds.has(edge.target) &&
      !existingIds.has(edge.id),
  );
  const edges = [...hierarchy.edges, ...semanticEdges];
  return {
    graph: {
      ...hierarchy,
      edges,
      meta: { ...hierarchy.meta, edge_count: edges.length },
    },
    semanticEdgeCount: semanticEdges.length,
  };
}

const TYPE_PRIORITY: Record<string, number> = {
  ResearchItem: 5,
  ResearchGap: 4,
  Concept: 3,
  AgentPattern: 3,
  BusinessDomain: 3,
  Technology: 2,
};

/** Rank labels for semantic zoom. The renderer still draws every node, but overview labels are
 * reserved for hubs and research anchors instead of becoming an illegible text wall. */
export function rankRelationshipLabels(nodes: GraphNode[]): Map<string, number> {
  const ranked = [...nodes].sort((left, right) => {
    const importance = (node: GraphNode) =>
      node.degree * 12 +
      node.source_count * 3 +
      (TYPE_PRIORITY[node.type] ?? 0) +
      (node.evidence_count ?? 0);
    return importance(right) - importance(left) || left.label.localeCompare(right.label);
  });
  return new Map(ranked.map((node, index) => [node.id, index]));
}

export function relationshipLabelBudget(nodeCount: number, zoom: number): number {
  const base = Math.max(10, Math.min(30, Math.round(Math.sqrt(nodeCount) * 1.25)));
  if (zoom < 0.55) return Math.max(6, Math.round(base * 0.45));
  if (zoom < 0.9) return Math.max(8, Math.round(base * 0.7));
  if (zoom < 1.45) return base;
  if (zoom < 2.2) return Math.min(nodeCount, base * 3);
  return nodeCount;
}
