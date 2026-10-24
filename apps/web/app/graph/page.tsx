"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { EdgeDetailsPanel } from "@/components/knowledge-graph/edge-details-panel";
import { EvidenceList } from "@/components/knowledge-graph/evidence-list";
import { D3GraphCanvas } from "@/components/knowledge-graph/d3-graph-canvas";
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
  graphClusterCount,
  isHierarchyEdgeType,
  mergeHierarchyRelationshipOverlay,
} from "@/lib/knowledge-graph/graph-visualization";
import type {
  GraphFilters as FilterState,
  GraphLayoutMode,
  GraphView,
} from "@/lib/knowledge-graph/types";

// Render the complete current local corpus in both layouts. The API retains the explicit
// 1,000-node operational ceiling; there is no longer a product-level 100-node display cap.
const GRAPH_DISPLAY_LIMIT = 1000;

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
  const [actionError, setActionError] = useState("");
  const [showExplorer, setShowExplorer] = useState(false);
  const [showLabels, setShowLabels] = useState(true);
  const [expandedLeafParentIds, setExpandedLeafParentIds] = useState<Set<string>>(new Set());
  const activeRootId = focusId;
  const baseLimit = GRAPH_DISPLAY_LIMIT;
  const graphQuery = useKnowledgeGraph(filters, {
    view,
    rootNodeId: view === "hierarchy" ? activeRootId : undefined,
    depth: 1,
    limit: baseLimit,
    enabled: true,
  });
  // The hierarchy API deliberately returns only parent/child edges. Load the accepted relationship
  // projection beside it so visible cards can retain their real semantic connections.
  const hierarchyRelationshipQuery = useKnowledgeGraph(filters, {
    view: "relationship",
    limit: baseLimit,
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
        semanticEdgeCount: 0,
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
      semanticEdgeCount: overlaid.semanticEdgeCount,
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
    const nodes = presentation.graph.nodes
      .filter((node) => !hiddenNodeIds.has(node.id))
      .map((node) => ({ ...node, expanded_group: false }));
    const ids = new Set(nodes.map((node) => node.id));
    const edges = presentation.graph.edges.filter(
      (edge) => ids.has(edge.source) && ids.has(edge.target),
    );
    return {
      ...presentation.graph,
      nodes,
      edges,
      meta: { ...presentation.graph.meta, node_count: nodes.length, edge_count: edges.length },
    };
  }, [
    hiddenNodeIds,
    presentation,
  ]);
  const unplacedNodeCount = presentation?.unplacedNodeCount ?? 0;
  const hiddenLeafCount = presentation?.hiddenLeafCount ?? 0;
  const semanticEdgeCount = presentation?.semanticEdgeCount ?? 0;

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
  const corpusCounts = useMemo(() => {
    const values: Record<string, number> = {};
    corpusGraph?.nodes.forEach((node) => { values[node.type] = (values[node.type] ?? 0) + 1; });
    return values;
  }, [corpusGraph?.nodes]);
  const clusterCount = useMemo(
    () => corpusGraph ? graphClusterCount(corpusGraph) : 0,
    [corpusGraph],
  );
  const topics = view === "relationship" ? graph?.nodes
    .filter((node) => node.type === "Concept")
    .sort((left, right) => right.degree - left.degree)
    .slice(0, 6) ?? [] : [];
  const selectedNode = selection.selection?.kind === "node" ? selection.selection.value : null;
  const selectedEdge = selection.selection?.kind === "edge" ? selection.selection.value : null;
  const selectedNodeInCurrentView = Boolean(selectedNode && nodeById.has(selectedNode.id));
  const relationships = selectedNode
    ? graph?.edges.filter(
        (edge) => edge.source === selectedNode.id || edge.target === selectedNode.id,
      ) ?? []
    : [];
  const relatedEvidence = selectedEdge?.evidence ?? relationships.flatMap((edge) => edge.evidence);
  const structuralEdgeCount = graph?.edges.filter((edge) => isHierarchyEdgeType(edge.type)).length ?? 0;
  // Metrics describe what is on screen. The wider totals are shown beside them rather
  // than in their place, so the header can never claim more than the canvas is drawing.
  const visibleMetrics = {
    nodes: graph?.nodes.length ?? 0,
    edges: graph?.edges.length ?? 0,
    clusters: view === "hierarchy"
      ? graph?.nodes.filter((node) => !graph.edges.some((edge) => edge.target === node.id)).length ?? 0
      : clusterCount,
  };
  const totalMetrics = {
    nodes: view === "hierarchy"
      ? graph?.meta.total_node_count ?? visibleMetrics.nodes
      : graph?.meta.total_node_count ?? visibleMetrics.nodes,
    edges: view === "hierarchy"
      ? graph?.meta.total_edge_count ?? visibleMetrics.edges
      : graph?.meta.total_edge_count ?? visibleMetrics.edges,
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

  async function expandNode(nodeId: string) {
    setActionError("");
    try {
      await graphQuery.expandNode(nodeId);
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : t("graphExpandFailed"));
    }
  }

  function resetGraph() {
    setFilters({ ...defaultGraphFilters });
    setHiddenNodeIds(new Set());
    selection.clearSelection();
    setActionError("");
    setFocusId(undefined);
    setShowExplorer(false);
    setShowLabels(true);
    setExpandedLeafParentIds(new Set());
  }

  /** Redraw the hierarchy around `nodeId`, which becomes the new breadcrumb tail. */
  function focusNode(nodeId: string | undefined) {
    setFocusId(nodeId);
    setActionError("");
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
            <strong>{view === "hierarchy" ? semanticEdgeCount : visibleMetrics.clusters}</strong>
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
        onSearch={(query) => setFilters({ ...filters, query })}
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
          {hiddenNodeCount > 0 && <span>{t("graphOperationalLimit")}</span>}
        </p>
      )}
      {actionError && <p className="error">{actionError}</p>}
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
                <button key={topic.id} onClick={() => setFilters({ ...filters, query: topic.label })}>
                  <span>{topic.label}</span><strong>{topic.degree}</strong>
                </button>
              ))}
            </section>
          )}
          <GraphFilters
            filters={filters}
            nodeTypes={Object.keys(corpusCounts).length > 0 ? Object.keys(corpusCounts) : Object.keys(counts)}
            view={view}
            onChange={setFilters}
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
              onNodeSelect={selection.selectNode}
              onEdgeSelect={selection.selectEdge}
              onClearSelection={selection.clearSelection}
              onExpandNode={view === "hierarchy" ? openNode : expandNode}
              hierarchyLabels={hierarchyLabels}
              status={{
                nodes: `${visibleMetrics.nodes} ${t("nodes")}`,
                edges: view === "hierarchy"
                  ? `${structuralEdgeCount} ${t("hierarchyLinks")}`
                  : `${visibleMetrics.edges} ${t("edges")}`,
                detail: view === "hierarchy"
                  ? [
                      `${semanticEdgeCount} ${t("semanticLinks")}`,
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
                .filter((edge) => edge.type === "PARENT_OF" && edge.source === selectedNode.id)
                .map((edge) => nodeById.get(edge.target))
                .filter((node): node is NonNullable<typeof node> => Boolean(node))}
              view={view}
              inCurrentView={selectedNodeInCurrentView}
              expanding={graphQuery.expandingNodeId === selectedNode.id}
              onExpand={() => expandNode(selectedNode.id)}
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
