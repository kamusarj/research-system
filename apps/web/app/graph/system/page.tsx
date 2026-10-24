"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { D3GraphCanvas } from "@/components/knowledge-graph/d3-graph-canvas-lazy";
import { GraphLegend } from "@/components/knowledge-graph/graph-legend";
import { GraphToolbar } from "@/components/knowledge-graph/graph-toolbar";
import { NodeDetailsPanel } from "@/components/knowledge-graph/node-details-panel";
import { useI18n } from "@/lib/i18n";
import { getSystemKnowledgeGraph } from "@/lib/knowledge-graph/graph-api";
import { buildSystemMapPresentation } from "@/lib/knowledge-graph/graph-visualization";
import type { GraphLayoutMode, GraphNode, KnowledgeGraph } from "@/lib/knowledge-graph/types";

function filterSystemMap(graph: KnowledgeGraph, search: string): KnowledgeGraph {
  const query = search.trim().toLocaleLowerCase();
  if (!query) return graph;

  const parentByChild = new Map<string, string>();
  graph.edges.forEach((edge) => {
    if (edge.type === "PARENT_OF" || edge.type === "BROADER_THAN") {
      parentByChild.set(edge.target, edge.source);
    }
  });
  const visibleIds = new Set(
    graph.nodes
      .filter((node) => [node.label, node.type, node.summary]
        .some((value) => value?.toLocaleLowerCase().includes(query)))
      .map((node) => node.id),
  );
  [...visibleIds].forEach((nodeId) => {
    let parentId = parentByChild.get(nodeId);
    while (parentId && !visibleIds.has(parentId)) {
      visibleIds.add(parentId);
      parentId = parentByChild.get(parentId);
    }
  });
  const nodes = graph.nodes.filter((node) => visibleIds.has(node.id));
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

export default function SystemKnowledgeMapPage() {
  const { t } = useI18n();
  const system = useQuery({
    queryKey: ["business-ai-agents-system-map"],
    queryFn: getSystemKnowledgeGraph,
  });
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [expandedPillarId, setExpandedPillarId] = useState<string | null>(null);
  const [layout, setLayout] = useState<GraphLayoutMode>("hierarchy");
  const [search, setSearch] = useState("");
  const [layoutNonce, setLayoutNonce] = useState(0);
  const [fitNonce, setFitNonce] = useState(0);
  const [showExplorer, setShowExplorer] = useState(false);
  const [showLabels, setShowLabels] = useState(true);
  const nodeById = useMemo(
    () => new Map(system.data?.nodes.map((node) => [node.id, node]) ?? []),
    [system.data?.nodes],
  );
  const relationships = selected
    ? system.data?.edges.filter(
        (edge) => edge.source === selected.id || edge.target === selected.id,
      ) ?? []
    : [];
  const childNodes = relationships
    .filter((edge) => edge.type === "PARENT_OF" && edge.source === selected?.id)
    .map((edge) => nodeById.get(edge.target))
    .filter((node): node is GraphNode => Boolean(node));
  const presentation = useMemo(
    () => {
      if (!system.data) return null;
      const base = layout === "hierarchy" && !search.trim()
        ? buildSystemMapPresentation(system.data, expandedPillarId)
        : system.data;
      return filterSystemMap(base, search);
    },
    [expandedPillarId, layout, search, system.data],
  );
  const counts = useMemo(() => {
    const values: Record<string, number> = {};
    presentation?.nodes.forEach((node) => {
      values[node.type] = (values[node.type] ?? 0) + 1;
    });
    return values;
  }, [presentation?.nodes]);

  function browseNode(nodeId: string) {
    const node = nodeById.get(nodeId);
    if (node) setSelected(node);
  }

  function togglePillar(nodeId: string) {
    const node = nodeById.get(nodeId);
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
  }

  function resetGraph() {
    setLayout("hierarchy");
    setSearch("");
    setSelected(null);
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
      {system.error && <div className="graph-state error-state"><h2>{t("graphLoadFailed")}</h2><p>{system.error.message}</p></div>}
      {system.data && presentation && (
        <section className="graph-studio system-map-studio">
          <GraphToolbar
            layout={layout}
            search={search}
            onLayoutChange={(nextLayout) => {
              setLayout(nextLayout);
              setLayoutNonce((value) => value + 1);
            }}
            onSearch={setSearch}
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
              <D3GraphCanvas
                nodes={presentation.nodes}
                edges={presentation.edges}
                layoutNonce={layoutNonce}
                fitNonce={fitNonce}
                layout={layout}
                labelsVisible={showLabels}
                onNodeSelect={setSelected}
                onEdgeSelect={() => undefined}
                onClearSelection={() => setSelected(null)}
                onExpandNode={togglePillar}
                hierarchyLabels={{
                  board: t("systemBoard"),
                  nodes: t("nodes"),
                  open: t("openNodeList"),
                  close: t("closeNodeList"),
                }}
                status={{
                  nodes: `${presentation.nodes.length} ${t("nodes")}`,
                  edges: `${presentation.edges.length} ${layout === "hierarchy" ? t("hierarchyLinks") : t("edges")}`,
                  detail: layout === "hierarchy" ? t("hierarchyView") : layout === "orbit" ? t("orbitView") : t("relationshipView"),
                }}
              />
            </section>
            {selected && (
              <aside className="graph-inspector">
                <NodeDetailsPanel
                  node={selected}
                  relationships={relationships}
                  childNodes={childNodes}
                  ontologyBacked
                  view={layout === "hierarchy" ? "hierarchy" : "relationship"}
                  inCurrentView
                  expanding={false}
                  onExpand={() => undefined}
                  onBrowseNode={browseNode}
                  onHide={() => setSelected(null)}
                />
              </aside>
            )}
          </div>
        </section>
      )}
    </>
  );
}
