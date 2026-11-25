"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { D3GraphCanvas } from "@/components/knowledge-graph/d3-graph-canvas-lazy";
import { EdgeDetailsPanel } from "@/components/knowledge-graph/edge-details-panel";
import { GraphLegend } from "@/components/knowledge-graph/graph-legend";
import { GraphToolbar } from "@/components/knowledge-graph/graph-toolbar";
import { NodeDetailsPanel } from "@/components/knowledge-graph/node-details-panel";
import { useGraphSelection } from "@/hooks/use-graph-selection";
import { useI18n } from "@/lib/i18n";
import { getSystemKnowledgeGraph } from "@/lib/knowledge-graph/graph-api";
import { buildSystemMapPresentation, excludeGraphNodes, isHierarchyEdgeType } from "@/lib/knowledge-graph/graph-visualization";
import type { GraphLayoutMode, GraphNode, KnowledgeGraph } from "@/lib/knowledge-graph/types";

function filterSystemMap(graph: KnowledgeGraph, search: string): KnowledgeGraph {
  const query = search.trim().toLocaleLowerCase();
  if (!query) return graph;

  const parentsByChild = new Map<string, Set<string>>();
  graph.edges.forEach((edge) => {
    if (!isHierarchyEdgeType(edge.type)) return;
    const parents = parentsByChild.get(edge.target) ?? new Set<string>();
    parents.add(edge.source);
    parentsByChild.set(edge.target, parents);
  });
  const visibleIds = new Set(
    graph.nodes
      .filter((node) => [node.label, node.type, node.summary]
        .some((value) => value?.toLocaleLowerCase().includes(query)))
      .map((node) => node.id),
  );
  for (const nodeId of visibleIds) {
    parentsByChild.get(nodeId)?.forEach((parentId) => {
      visibleIds.add(parentId);
    });
  }
  return excludeGraphNodes(
    graph,
    new Set(graph.nodes.filter((node) => !visibleIds.has(node.id)).map((node) => node.id)),
  );
}

export default function SystemKnowledgeMapPage() {
  const { t } = useI18n();
  const system = useQuery({
    queryKey: ["business-ai-agents-system-map"],
    queryFn: getSystemKnowledgeGraph,
  });
  const selection = useGraphSelection();
  const [hiddenNodeIds, setHiddenNodeIds] = useState<Set<string>>(new Set());
  const [expandedPillarId, setExpandedPillarId] = useState<string | null>(null);
  const [layout, setLayout] = useState<GraphLayoutMode>("hierarchy");
  const [search, setSearch] = useState("");
  const [layoutNonce, setLayoutNonce] = useState(0);
  const [fitNonce, setFitNonce] = useState(0);
  const [showExplorer, setShowExplorer] = useState(false);
  const [showLabels, setShowLabels] = useState(true);
  const hierarchyLabels = useMemo(() => ({
    board: t("systemBoard"),
    nodes: t("nodes"),
    open: t("openNodeList"),
    close: t("closeNodeList"),
  }), [t]);
  const nodeById = useMemo(
    () => new Map(system.data?.nodes.map((node) => [node.id, node]) ?? []),
    [system.data?.nodes],
  );
  const structuralEdges = useMemo(
    () => system.data?.edges.filter((edge) => isHierarchyEdgeType(edge.type)) ?? [],
    [system.data?.edges],
  );
  const presentation = useMemo(
    () => {
      if (!system.data) return null;
      const base = layout === "hierarchy" && !search.trim()
        ? buildSystemMapPresentation(system.data, expandedPillarId)
        : system.data;
      return excludeGraphNodes(filterSystemMap(base, search), hiddenNodeIds);
    },
    [expandedPillarId, hiddenNodeIds, layout, search, system.data],
  );
  const visibleNodes = useMemo(
    () => new Map(presentation?.nodes.map((node) => [node.id, node]) ?? []),
    [presentation?.nodes],
  );
  const selectedNode = selection.selection?.kind === "node"
    ? visibleNodes.get(selection.selection.value.id) : undefined;
  const selectedEdgeId = selection.selection?.kind === "edge" ? selection.selection.value.id : null;
  const selectedEdge = presentation?.edges.find((edge) => edge.id === selectedEdgeId);
  const relationships = selectedNode
    ? system.data?.edges.filter(
        (edge) => edge.source === selectedNode.id || edge.target === selectedNode.id,
      ) ?? []
    : [];
  const childNodeIds = new Set(
    structuralEdges
      .filter((edge) => edge.source === selectedNode?.id && !hiddenNodeIds.has(edge.target))
      .map((edge) => edge.target),
  );
  const childNodes = [...childNodeIds]
    .map((id) => nodeById.get(id))
    .filter((node): node is GraphNode => Boolean(node));
  const counts = useMemo(() => {
    const values: Record<string, number> = {};
    presentation?.nodes.forEach((node) => {
      values[node.type] = (values[node.type] ?? 0) + 1;
    });
    return values;
  }, [presentation?.nodes]);

  function browseNode(nodeId: string) {
    const node = nodeById.get(nodeId);
    if (!node || hiddenNodeIds.has(nodeId)) return;
    if (!visibleNodes.has(nodeId) && layout === "hierarchy") {
      const pillar = structuralEdges.find((edge) =>
        edge.target === nodeId && nodeById.get(edge.source)?.type === "SystemPillar",
      );
      if (pillar && !hiddenNodeIds.has(pillar.source)) {
        setSearch("");
        setExpandedPillarId(pillar.source);
      } else {
        setSearch(node.label);
      }
    }
    selection.selectNode(node);
  }

  function togglePillar(nodeId: string) {
    const node = visibleNodes.get(nodeId);
    if (
      layout !== "hierarchy" ||
      search.trim() ||
      node?.type !== "SystemPillar" ||
      (node.child_count ?? 0) === 0
    ) {
      browseNode(nodeId);
      return;
    }
    setExpandedPillarId((current) => current === nodeId ? null : nodeId);
    selection.selectNode(node);
  }

  function resetGraph() {
    setLayout("hierarchy");
    setSearch("");
    selection.clearSelection();
    setHiddenNodeIds(new Set());
    setExpandedPillarId(null);
    setShowExplorer(false);
    setShowLabels(true);
    setLayoutNonce((value) => value + 1);
    setFitNonce((value) => value + 1);
  }

  return (
    <>
      <header className="page-header graph-page-header graph-studio-heading system-map-heading">
        <div>
          <h1>{t("systemKnowledgeMap")}</h1>
        </div>
        <div className="metric-row">
          <Link className="back-link button-link" href="/graph">← {t("backToKnowledgeGraph")}</Link>
          <span>
            <strong>{presentation?.nodes.length ?? 0}</strong>{t("nodes")}
            {system.data && presentation && presentation.nodes.length < system.data.nodes.length && (
              <small>{t("ofTotal").replace("{total}", String(system.data.nodes.length))}</small>
            )}
          </span>
          <span>
            <strong>{presentation?.edges.length ?? 0}</strong>{t("edges")}
            {system.data && presentation && presentation.edges.length < system.data.edges.length && (
              <small>{t("ofTotal").replace("{total}", String(system.data.edges.length))}</small>
            )}
          </span>
        </div>
      </header>
      {system.isLoading && <div className="graph-state"><span className="spinner" />{t("loading")}</div>}
      {system.error && (
        <div className="graph-state error-state">
          <h2>{t("graphLoadFailed")}</h2>
          <p>{system.error.message}</p>
          <button type="button" onClick={() => system.refetch()}>{t("retry")}</button>
        </div>
      )}
      {system.data && presentation && (
        <section className="graph-studio system-map-studio">
          <GraphToolbar
            layout={layout}
            search={search}
            onLayoutChange={(nextLayout) => {
              setLayout(nextLayout);
              setLayoutNonce((value) => value + 1);
            }}
            onSearch={(query) => {
              setSearch(query);
              selection.clearSelection();
            }}
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
          <div className={`graph-workspace system-map-workspace ${showExplorer ? "explorer-open" : "explorer-closed"}`}>
            <aside className="graph-left-panel" aria-hidden={!showExplorer}>
              <GraphLegend counts={counts} />
            </aside>
            <section className="graph-center">
              {presentation.nodes.length === 0 ? (
                <div className="graph-state empty-state">{t(search.trim() ? "noSearchMatches" : "graphEmpty")}</div>
              ) : <D3GraphCanvas
                nodes={presentation.nodes}
                edges={presentation.edges}
                layoutNonce={layoutNonce}
                fitNonce={fitNonce}
                layout={layout}
                labelsVisible={showLabels}
                selectedNodeId={selectedNode?.id ?? null}
                selectedEdgeId={selectedEdge?.id ?? null}
                onNodeSelect={selection.selectNode}
                onEdgeSelect={selection.selectEdge}
                onClearSelection={selection.clearSelection}
                onExpandNode={togglePillar}
                hierarchyLabels={hierarchyLabels}
                status={{
                  nodes: `${presentation.nodes.length} ${t("nodes")}`,
                  edges: `${presentation.edges.length} ${layout === "hierarchy" ? t("hierarchyLinks") : t("edges")}`,
                  detail: layout === "hierarchy" ? t("hierarchyView") : layout === "orbit" ? t("orbitView") : t("relationshipView"),
                }}
              />}
            </section>
            {(selectedNode || selectedEdge) && (
              <aside className="graph-inspector">
                {selectedNode && (
                  <NodeDetailsPanel
                    key={selectedNode.id}
                    node={selectedNode}
                    relationships={relationships}
                    childNodes={childNodes}
                    view={layout === "hierarchy" ? "hierarchy" : "relationship"}
                    inCurrentView
                    expanding={false}
                    onBrowseNode={(nodeId) => nodeId === selectedNode.id ? togglePillar(nodeId) : browseNode(nodeId)}
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
              </aside>
            )}
          </div>
        </section>
      )}
    </>
  );
}
