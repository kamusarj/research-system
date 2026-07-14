"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { EdgeDetailsPanel } from "@/components/knowledge-graph/edge-details-panel";
import { EvidenceList } from "@/components/knowledge-graph/evidence-list";
import { GraphCanvas } from "@/components/knowledge-graph/graph-canvas";
import { GraphFilters } from "@/components/knowledge-graph/graph-filters";
import { GraphLegend } from "@/components/knowledge-graph/graph-legend";
import { GraphToolbar } from "@/components/knowledge-graph/graph-toolbar";
import { NodeDetailsPanel } from "@/components/knowledge-graph/node-details-panel";
import { defaultGraphFilters, useKnowledgeGraph } from "@/hooks/use-knowledge-graph";
import { useGraphSelection } from "@/hooks/use-graph-selection";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { GraphFilters as FilterState } from "@/lib/knowledge-graph/types";

type Stats = { nodes: number; edges: number; clusters: number; by_type: Record<string, number> };

export default function KnowledgeGraphPage() {
  const { t } = useI18n();
  const [filters, setFilters] = useState<FilterState>({ ...defaultGraphFilters });
  const [hiddenNodeIds, setHiddenNodeIds] = useState<Set<string>>(new Set());
  const [layoutNonce, setLayoutNonce] = useState(0);
  const [fitNonce, setFitNonce] = useState(0);
  const [actionError, setActionError] = useState("");
  const graphQuery = useKnowledgeGraph(filters);
  const stats = useQuery({ queryKey: ["graph-stats"], queryFn: () => api<Stats>("/graph/stats") });
  const selection = useGraphSelection();

  const graph = useMemo(() => {
    if (!graphQuery.graph) return undefined;
    const nodes = graphQuery.graph.nodes.filter((node) => !hiddenNodeIds.has(node.id));
    const ids = new Set(nodes.map((node) => node.id));
    const edges = graphQuery.graph.edges.filter(
      (edge) => ids.has(edge.source) && ids.has(edge.target),
    );
    return { ...graphQuery.graph, nodes, edges };
  }, [graphQuery.graph, hiddenNodeIds]);

  const nodeById = useMemo(
    () => new Map(graph?.nodes.map((node) => [node.id, node]) ?? []),
    [graph?.nodes],
  );
  const counts = useMemo(() => {
    const values: Record<string, number> = {};
    graph?.nodes.forEach((node) => { values[node.type] = (values[node.type] ?? 0) + 1; });
    return values;
  }, [graph?.nodes]);
  const topics = graph?.nodes
    .filter((node) => node.type === "Concept")
    .sort((left, right) => right.degree - left.degree)
    .slice(0, 8) ?? [];
  const selectedNode = selection.selection?.kind === "node" ? selection.selection.value : null;
  const selectedEdge = selection.selection?.kind === "edge" ? selection.selection.value : null;
  const relationships = selectedNode
    ? graph?.edges.filter(
        (edge) => edge.source === selectedNode.id || edge.target === selectedNode.id,
      ) ?? []
    : [];
  const relatedEvidence = selectedEdge?.evidence ?? relationships.flatMap((edge) => edge.evidence);

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
  }

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">{t("graphProjection")}</p>
          <h1>{t("graphTitle")}</h1>
          <p className="muted">{t("graphIntro")}</p>
        </div>
        <div className="metric-row">
          <span><strong>{stats.data?.nodes ?? 0}</strong>{t("nodes")}</span>
          <span><strong>{stats.data?.edges ?? 0}</strong>{t("edges")}</span>
          <span><strong>{stats.data?.clusters ?? 0}</strong>{t("clusters")}</span>
        </div>
      </header>
      <GraphToolbar
        search={filters.query}
        onSearch={(query) => setFilters({ ...filters, query })}
        onFit={() => setFitNonce((value) => value + 1)}
        onReset={resetGraph}
        onRelayout={() => setLayoutNonce((value) => value + 1)}
        labels={{ search: t("findNode"), fit: t("fit"), reset: t("reset"), relayout: t("relayout") }}
      />
      {graph?.meta.provider !== "postgres" && graph && (
        <p className="graph-notice">{t("graphProvider")}: {graph.meta.provider}</p>
      )}
      {graph?.meta.truncated && <p className="graph-warning">{t("graphTruncated")}</p>}
      {actionError && <p className="error">{actionError}</p>}
      <div className="graph-workspace">
        <aside className="graph-left-panel">
          <section className="card topic-panel">
            <h3>{t("topics")}</h3>
            {topics.map((topic) => (
              <button key={topic.id} onClick={() => setFilters({ ...filters, query: topic.label })}>
                <span>{topic.label}</span><strong>{topic.degree}</strong>
              </button>
            ))}
            {!topics.length && <p className="muted">{t("noTopics")}</p>}
          </section>
          <GraphFilters
            filters={filters}
            nodeTypes={Object.keys(stats.data?.by_type ?? counts)}
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
          {graphQuery.isLoading && <div className="graph-state"><span className="spinner" />{t("loading")}</div>}
          {graphQuery.error && (
            <div className="graph-state error-state">
              <h2>{t("graphLoadFailed")}</h2>
              <p>{graphQuery.error.message}</p>
              <button onClick={() => graphQuery.refetch()}>{t("retry")}</button>
            </div>
          )}
          {!graphQuery.isLoading && !graphQuery.error && graph?.nodes.length === 0 && (
            <div className="graph-state empty-state">
              <span>⌘</span><h2>{t("graphEmpty")}</h2><p>{t("graphEmptyHint")}</p>
            </div>
          )}
          {!graphQuery.isLoading && !graphQuery.error && graph && graph.nodes.length > 0 && (
            <GraphCanvas
              nodes={graph.nodes}
              edges={graph.edges}
              layoutNonce={layoutNonce}
              fitNonce={fitNonce}
              onNodeSelect={selection.selectNode}
              onEdgeSelect={selection.selectEdge}
              onClearSelection={selection.clearSelection}
              onExpandNode={expandNode}
            />
          )}
        </section>
        <aside className="graph-inspector">
          {selectedNode && (
            <NodeDetailsPanel
              node={selectedNode}
              relationships={relationships}
              expanding={graphQuery.expandingNodeId === selectedNode.id}
              onExpand={() => expandNode(selectedNode.id)}
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
          {!selection.selection && (
            <div className="card detail-panel">
              <p className="eyebrow">{t("nodeInspector")}</p>
              <p className="muted">{t("selectNode")}</p>
            </div>
          )}
        </aside>
      </div>
      <section className="card graph-evidence-panel">
        <div><p className="eyebrow">{t("evidence")}</p><h2>{t("relatedEvidence")}</h2></div>
        <EvidenceList evidence={relatedEvidence} />
      </section>
    </>
  );
}
