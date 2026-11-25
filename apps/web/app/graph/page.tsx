"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { EdgeDetailsPanel } from "@/components/knowledge-graph/edge-details-panel";
import { EvidenceList } from "@/components/knowledge-graph/evidence-list";
import { D3GraphCanvas } from "@/components/knowledge-graph/d3-graph-canvas-lazy";
import { GraphFilters } from "@/components/knowledge-graph/graph-filters";
import { GraphLegend } from "@/components/knowledge-graph/graph-legend";
import { GraphToolbar } from "@/components/knowledge-graph/graph-toolbar";
import { NodeDetailsPanel } from "@/components/knowledge-graph/node-details-panel";
import { defaultGraphFilters, useKnowledgeGraph } from "@/hooks/use-knowledge-graph";
import { useGraphSelection } from "@/hooks/use-graph-selection";
import { useI18n } from "@/lib/i18n";
import {
  buildGraphPresentation,
  collapseDenseHierarchyLeaves,
  excludeGraphNodes,
  graphClusterCount,
  isHierarchyTreeEdge,
  mergeHierarchyRelationshipOverlay,
} from "@/lib/knowledge-graph/graph-visualization";
import type {
  GraphFilters as FilterState,
  GraphLayoutMode,
  GraphView,
} from "@/lib/knowledge-graph/types";

export default function KnowledgeGraphPage() {
  const { t } = useI18n();
  const [layout, setLayout] = useState<GraphLayoutMode>("hierarchy");
  const view: GraphView = layout === "hierarchy" ? "hierarchy" : "relationship";
  // Which node the knowledge hierarchy is currently drawn around. Undefined shows the full forest.
  const [focusId, setFocusId] = useState<string>();
  const [filters, setFilters] = useState<FilterState>({ ...defaultGraphFilters });
  const [hiddenNodeIds, setHiddenNodeIds] = useState<Set<string>>(new Set());
  const [layoutNonce, setLayoutNonce] = useState(0);
  const [fitNonce, setFitNonce] = useState(0);
  const [showExplorer, setShowExplorer] = useState(false);
  const [showLabels, setShowLabels] = useState(true);
  const [expandedLeafParentIds, setExpandedLeafParentIds] = useState<Set<string>>(new Set());
  const activeRootId = focusId;
  const activeFilters = useMemo(() => view === "hierarchy" ? {
    ...filters,
    sourceTypes: [],
    minConfidence: 0,
    dateFrom: "",
    dateTo: "",
  } : filters, [filters, view]);
  const hasFilters = Boolean(activeFilters.query.trim() || activeFilters.nodeTypes.length ||
    activeFilters.sourceTypes.length || activeFilters.minConfidence ||
    activeFilters.dateFrom || activeFilters.dateTo);
  const filterCatalog = useKnowledgeGraph(defaultGraphFilters, {
    view: "relationship",
    full: true,
    enabled: showExplorer && hasFilters,
  });
  const graphQuery = useKnowledgeGraph(activeFilters, {
    view,
    rootNodeId: view === "hierarchy" ? activeRootId : undefined,
    depth: 1,
    full: true,
    enabled: true,
  });
  // The hierarchy API deliberately returns only parent/child edges. Load the accepted relationship
  // projection beside it so visible cards can retain their real semantic connections.
  const hierarchyRelationshipQuery = useKnowledgeGraph(activeFilters, {
    view: "relationship",
    full: true,
    enabled: view === "hierarchy",
  });
  const selection = useGraphSelection();

  const presentation = useMemo(() => {
    if (!graphQuery.graph) return undefined;
    const base = buildGraphPresentation(
      graphQuery.graph,
      view,
      Boolean(activeRootId || filters.query.trim()),
    );
    if (view !== "hierarchy") {
      return {
        ...base,
        hiddenLeafCount: 0,
        collapsedParentCount: 0,
      };
    }
    const progressive = collapseDenseHierarchyLeaves(base.graph, expandedLeafParentIds);
    const overlaid = mergeHierarchyRelationshipOverlay(
      progressive.graph,
      hierarchyRelationshipQuery.graph,
    );
    return {
      ...base,
      graph: overlaid.graph,
      hiddenLeafCount: progressive.hiddenLeafCount,
      collapsedParentCount: progressive.collapsedParentCount,
    };
  }, [
    activeRootId,
    expandedLeafParentIds,
    filters.query,
    graphQuery.graph,
    hierarchyRelationshipQuery.graph,
    view,
  ]);
  const graph = useMemo(() => {
    if (!presentation) return undefined;
    const visible = excludeGraphNodes(presentation.graph, hiddenNodeIds);
    return {
      ...visible,
      nodes: visible.nodes.map((node) => ({ ...node, expanded_group: false })),
    };
  }, [
    hiddenNodeIds,
    presentation,
  ]);
  const unplacedNodeCount = presentation?.unplacedNodeCount ?? 0;
  const hiddenLeafCount = presentation?.hiddenLeafCount ?? 0;

  const nodeById = useMemo(
    () => new Map(graph?.nodes.map((node) => [node.id, node]) ?? []),
    [graph?.nodes],
  );
  const counts = useMemo(() => {
    const values: Record<string, number> = {};
    graph?.nodes.forEach((node) => { values[node.type] = (values[node.type] ?? 0) + 1; });
    return values;
  }, [graph?.nodes]);
  const corpusGraph = view === "hierarchy"
    ? hierarchyRelationshipQuery.graph
    : graphQuery.graph;
  const filterNodeTypes = useMemo(() => {
    const types = new Set(filters.nodeTypes);
    filterCatalog.graph?.nodes.forEach((node) => types.add(node.type));
    corpusGraph?.nodes.forEach((node) => types.add(node.type));
    graph?.nodes.forEach((node) => types.add(node.type));
    return [...types].sort();
  }, [corpusGraph?.nodes, filterCatalog.graph?.nodes, filters.nodeTypes, graph?.nodes]);
  const clusterCount = useMemo(
    () => corpusGraph ? graphClusterCount(corpusGraph) : 0,
    [corpusGraph],
  );
  const topics = view === "relationship" ? graph?.nodes
    .filter((node) => node.type === "Concept")
    .sort((left, right) => right.degree - left.degree)
    .slice(0, 6) ?? [] : [];
  const selectedNode = selection.selection?.kind === "node"
    ? nodeById.get(selection.selection.value.id) : undefined;
  const selectedEdgeId = selection.selection?.kind === "edge" ? selection.selection.value.id : null;
  const selectedEdge = graph?.edges.find((edge) => edge.id === selectedEdgeId);
  const relationships = selectedNode
    ? graph?.edges.filter(
        (edge) => edge.source === selectedNode.id || edge.target === selectedNode.id,
      ) ?? []
    : [];
  const relatedEvidence = selectedEdge?.evidence ?? relationships.flatMap((edge) => edge.evidence);
  const treeEdges = view === "hierarchy" ? graph?.edges.filter(isHierarchyTreeEdge) : undefined;
  const structuralEdgeCount = treeEdges?.length ?? 0;
  const semanticEdgeCount = view === "hierarchy" ? (graph?.edges.length ?? 0) - structuralEdgeCount : 0;
  const treeChildren = new Set(treeEdges?.map((edge) => edge.target));
  // Metrics describe what is on screen. The wider totals are shown beside them rather
  // than in their place, so the header can never claim more than the canvas is drawing.
  const visibleMetrics = {
    nodes: graph?.nodes.length ?? 0,
    edges: graph?.edges.length ?? 0,
    clusters: view === "hierarchy"
      ? graph?.nodes.filter((node) => !treeChildren.has(node.id)).length ?? 0
      : clusterCount,
  };
  const totalMetrics = {
    nodes: graph?.meta.total_node_count ?? visibleMetrics.nodes,
    edges: graph?.meta.total_edge_count ?? visibleMetrics.edges,
  };
  // A focus node drawn on its own means the branch is real but has nothing in it yet.
  // Ten of the eleven pillars were in exactly this state and rendered as a blank canvas.
  const isEmptyBranch = Boolean(
    graph && graph.nodes.length === 1 && graph.nodes[0].id === activeRootId,
  );
  const hiddenNodeCount = Math.max(
    0,
    (graph?.meta.total_node_count ?? 0) - visibleMetrics.nodes,
  );
  const hierarchyLabels = useMemo(() => ({
    board: t("systemBoard"),
    nodes: t("nodes"),
    open: t("openNodeList"),
    close: t("closeNodeList"),
  }), [t]);
  const loadError = graphQuery.error;
  const loading = graphQuery.isLoading;
  const overlayError = view === "hierarchy" && hierarchyRelationshipQuery.error;
  const overlayLoading = view === "hierarchy" && hierarchyRelationshipQuery.isLoading;
  const semanticMetric = overlayError || overlayLoading ? "—" : semanticEdgeCount;
  const actionError = graphQuery.expansionError;

  function replaceFilters(next: FilterState) {
    setFilters(next);
    graphQuery.resetExpansion();
    selection.clearSelection();
    setFocusId(undefined);
    setExpandedLeafParentIds(new Set());
  }

  function resetGraph() {
    replaceFilters({ ...defaultGraphFilters });
    setHiddenNodeIds(new Set());
    setShowExplorer(false);
    setShowLabels(true);
  }

  /** Redraw the hierarchy around `nodeId`, which becomes the new breadcrumb tail. */
  function focusNode(nodeId: string | undefined) {
    setFocusId(nodeId);
    setLayoutNonce((value) => value + 1);
  }

  /**
   * Open a node in the way that suits it.
   *
   * A pillar sitting directly under the current focus unfolds in place, which is the
   * compound-board behaviour the owner accepted. Anything deeper becomes the new focus,
   * so a branch is never a dead end just because it is three levels down.
   */
  function openNode(nodeId: string) {
    const node = graph?.nodes.find((item) => item.id === nodeId);
    if (!node) {
      // The child list in the inspector can name nodes that are not drawn yet, so an
      // unknown ID means "go there" rather than "do nothing".
      focusNode(nodeId);
      return;
    }
    selection.selectNode(node);
    if (node.leaf_group_expanded || (node.collapsed_leaf_count ?? 0) > 0) {
      setExpandedLeafParentIds((current) => {
        const next = new Set(current);
        if (next.has(nodeId)) next.delete(nodeId);
        else next.add(nodeId);
        return next;
      });
      setLayoutNonce((value) => value + 1);
      return;
    }
    if (node.id === activeRootId || (node.child_count ?? 0) === 0) return;
    focusNode(nodeId);
  }

  return (
    <>
      <header className="page-header graph-page-header graph-studio-heading">
        <div>
          <h1>{t("graphTitle")}</h1>
        </div>
        <div className="metric-row">
          <Link className="button-link secondary" href="/graph/system">{t("openSystemMap")}</Link>
          <span>
            <strong>{visibleMetrics.nodes}</strong>{t("nodes")}
            {totalMetrics.nodes > visibleMetrics.nodes && (
              <small>{t("ofTotal").replace("{total}", String(totalMetrics.nodes))}</small>
            )}
          </span>
          <span>
            <strong>{view === "hierarchy" ? structuralEdgeCount : visibleMetrics.edges}</strong>{t("edges")}
            {totalMetrics.edges > (view === "hierarchy" ? structuralEdgeCount : visibleMetrics.edges) && (
              <small>{t("ofTotal").replace("{total}", String(totalMetrics.edges))}</small>
            )}
          </span>
          <span>
            <strong>{view === "hierarchy" ? semanticMetric : visibleMetrics.clusters}</strong>
            {view === "hierarchy" ? t("semanticLinks") : t("clusters")}
          </span>
        </div>
      </header>
      <section className="graph-studio">
      <GraphToolbar
        layout={layout}
        search={filters.query}
        onLayoutChange={(nextLayout) => {
          setLayout(nextLayout);
          setLayoutNonce((value) => value + 1);
        }}
        onSearch={(query) => replaceFilters({ ...filters, query })}
        onFit={() => setFitNonce((value) => value + 1)}
        onReset={resetGraph}
        onRelayout={() => setLayoutNonce((value) => value + 1)}
        explorerOpen={showExplorer}
        onToggleExplorer={() => setShowExplorer((current) => !current)}
        labelsVisible={showLabels}
        onToggleLabels={() => setShowLabels((current) => !current)}
        labels={{
          search: t("findNode"),
          fit: t("fit"),
          reset: t("reset"),
          relayout: t("relayout"),
          relationship: t("relationshipView"),
          hierarchy: t("hierarchyView"),
          orbit: t("orbitView"),
          explorer: t("graphExplorer"),
          labels: t("graphLabels"),
        }}
      />
      {graph?.meta.provider !== "postgres" && graph && (
        <p className="graph-notice">{t("graphProvider")}: {graph.meta.provider}</p>
      )}
      {graph?.meta.truncated && (
        <p className="graph-warning">
          {t("graphTruncatedCount")
            .replace("{shown}", String(visibleMetrics.nodes))
            .replace("{total}", String(graph.meta.total_node_count ?? visibleMetrics.nodes))}
          {hiddenNodeCount > 0 && graph.meta.node_limit != null && (
            <span>{t("graphOperationalLimit").replace("{limit}", graph.meta.node_limit.toLocaleString("vi-VN"))}</span>
          )}
        </p>
      )}
      {actionError != null && (
        <p className="error" role="alert">
          {actionError instanceof Error ? actionError.message : t("graphExpandFailed")}
        </p>
      )}
      {overlayError && !loadError && (
        <div className="graph-warning" role="status">
          <span>{t("graphRelationsLoadFailed")} </span>
          <button type="button" onClick={() => hierarchyRelationshipQuery.refetch()}>{t("retry")}</button>
        </div>
      )}
      {/* Selection is otherwise a purely visual event, invisible to a screen reader. */}
      <p className="visually-hidden" role="status" aria-live="polite">
        {selectedNode
          ? t("selectedNodeAnnouncement")
              .replace("{label}", selectedNode.label)
              .replace("{type}", t(`nodeType.${selectedNode.type}`))
          : ""}
      </p>
      <div className={`graph-workspace ${showExplorer ? "explorer-open" : "explorer-closed"}`}>
        <aside className="graph-left-panel" aria-hidden={!showExplorer}>
          {topics.length > 0 && (
            <section className="card topic-panel">
              <h3>{t("topics")}</h3>
              {topics.map((topic) => (
                <button key={topic.id} onClick={() => replaceFilters({ ...filters, query: topic.label })}>
                  <span>{topic.label}</span><strong>{topic.degree}</strong>
                </button>
              ))}
            </section>
          )}
          <GraphFilters
            filters={filters}
            nodeTypes={filterNodeTypes}
            view={view}
            onChange={replaceFilters}
            labels={{
              filters: t("filters"),
              nodeTypes: t("nodeTypes"),
              sources: t("sources"),
              confidence: t("confidence"),
              time: t("timeRange"),
            }}
          />
          <GraphLegend counts={counts} />
        </aside>
        <section className="graph-center">
          {loading && (
            <div className="graph-state"><span className="spinner" />{t("loading")}</div>
          )}
          {loadError && (
            <div className="graph-state error-state">
              <h2>{t("graphLoadFailed")}</h2>
              <p>{loadError.message}</p>
              <button onClick={() => {
                graphQuery.refetch();
              }}>{t("retry")}</button>
            </div>
          )}
          {!loading && !loadError && graph?.nodes.length === 0 && (
            <div className="graph-state empty-state">
              <span>⌘</span><h2>{t("graphEmpty")}</h2><p>{t("graphEmptyHint")}</p>
              <Link className="detail-link primary" href="/ingestion">{t("openIntake")}</Link>
            </div>
          )}
          {!loading && !loadError && view === "hierarchy" && isEmptyBranch && (
            <div className="graph-state empty-state" data-testid="empty-branch">
              <span>▦</span>
              <h2>{t("emptyBranchTitle")}</h2>
              <p>{t("emptyBranchHint")}</p>
              <Link className="detail-link primary" href="/ingestion">{t("openIntake")}</Link>
            </div>
          )}
          {!loading && !loadError && graph && graph.nodes.length > 0 && (
            <D3GraphCanvas
              nodes={graph.nodes}
              edges={graph.edges}
              layoutNonce={layoutNonce}
              fitNonce={fitNonce}
              layout={layout}
              labelsVisible={showLabels}
              selectedNodeId={selectedNode?.id ?? null}
              selectedEdgeId={selectedEdge?.id ?? null}
              onNodeSelect={selection.selectNode}
              onEdgeSelect={selection.selectEdge}
              onClearSelection={selection.clearSelection}
              onExpandNode={view === "hierarchy" ? openNode : graphQuery.expandNode}
              hierarchyLabels={hierarchyLabels}
              status={{
                nodes: `${visibleMetrics.nodes} ${t("nodes")}`,
                edges: view === "hierarchy"
                  ? `${structuralEdgeCount} ${t("hierarchyLinks")}`
                  : `${visibleMetrics.edges} ${t("edges")}`,
                detail: view === "hierarchy"
                  ? [
                      `${semanticMetric} ${t("semanticLinks")}`,
                      hiddenLeafCount > 0 ? `${hiddenLeafCount} ${t("hiddenLeaves")}` : "",
                      unplacedNodeCount > 0 ? `${unplacedNodeCount} ${t("unplaced")}` : "",
                    ].filter(Boolean).join(" · ")
                  : `${visibleMetrics.clusters} ${t("clusters")}`,
              }}
            />
          )}
        </section>
        {(selectedNode || selectedEdge) && <aside className="graph-inspector">
          {selectedNode && (
            <NodeDetailsPanel
              key={selectedNode.id}
              node={selectedNode}
              relationships={relationships}
              childNodes={relationships
                .filter((edge) => isHierarchyTreeEdge(edge) && edge.source === selectedNode.id)
                .map((edge) => nodeById.get(edge.target))
                .filter((node): node is NonNullable<typeof node> => Boolean(node))}
              view={view}
              inCurrentView
              expanding={graphQuery.expandingNodeIds.has(selectedNode.id)}
              onExpand={() => graphQuery.expandNode(selectedNode.id)}
              onBrowseNode={openNode}
              onHide={() => {
                setHiddenNodeIds((current) => new Set(current).add(selectedNode.id));
                selection.clearSelection();
              }}
            />
          )}
          {selectedEdge && (
            <EdgeDetailsPanel
              edge={selectedEdge}
              source={nodeById.get(selectedEdge.source)}
              target={nodeById.get(selectedEdge.target)}
            />
          )}
        </aside>}
      </div>
      </section>
      {relatedEvidence.length > 0 && (
        <section className="card graph-evidence-panel">
          <div><p className="eyebrow">{t("evidence")}</p><h2>{t("relatedEvidence")}</h2></div>
          <EvidenceList evidence={relatedEvidence} />
        </section>
      )}
    </>
  );
}
