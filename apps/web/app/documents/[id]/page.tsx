"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { DocumentGraphCanvas } from "@/components/document-graph-canvas";
import { DocumentAIEditor } from "@/components/document-ai-editor";
import { DocumentSourceViewer } from "@/components/document-source-viewer";
import { StatusBadge } from "@/components/status-badge";
import { api, API_URL, vietnameseApiErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { queueDocument, researchDocumentGraph } from "@/lib/documents";
import { createDocumentChangeSet } from "@/lib/graph-changes";
import { useI18n } from "@/lib/i18n";
import type { DocumentContent, DocumentGraph, DocumentGraphNode, DocumentWorkspace } from "@/lib/types";

const activeStatuses = ["uploaded", "queued", "processing", "extracting", "evaluating", "graph_building"];
const comparisonTranslation = {
  consistent: "aiComparisonConsistent",
  different: "aiComparisonDifferent",
  insufficient: "aiComparisonInsufficient",
} as const;

export default function DocumentWorkspaceDetail() {
  const { t } = useI18n();
  const { can, user } = useAuth();
  const { id } = useParams<{ id: string }>();
  const [selected, setSelected] = useState<DocumentGraphNode | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [creatingChangeSet, setCreatingChangeSet] = useState(false);
  const [researchingNodeId, setResearchingNodeId] = useState<string | null>(null);
  const [researchingGraph, setResearchingGraph] = useState(false);
  const workspace = useQuery({
    queryKey: ["document-workspace", id],
    queryFn: () => api<DocumentWorkspace>(`/documents/${id}`),
    refetchInterval: (query) => activeStatuses.includes(query.state.data?.processing_status ?? "") ? 2000 : false,
  });
  const graph = useQuery({
    queryKey: ["document-workspace-graph", id, workspace.data?.graph_node_count],
    queryFn: () => api<DocumentGraph>(`/documents/${id}/graph`),
    enabled: Boolean(workspace.data?.graph_node_count),
  });
  const content = useQuery({
    queryKey: ["document-workspace-content", id, workspace.data?.source_version],
    queryFn: () => api<DocumentContent>(`/documents/${id}/content`),
    enabled: Boolean(workspace.data),
  });

  async function retry() {
    setActionError(null);
    try {
      await queueDocument(id, workspace.data?.processing_status === "failed" ? "retry" : "analyze");
      await workspace.refetch();
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : t("actionFailed"));
    }
  }

  async function createChangeSet() {
    setCreatingChangeSet(true);
    setActionError(null);
    try {
      const result = await createDocumentChangeSet(id);
      window.location.assign(`/graph/changes/${result.id}`);
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : t("actionFailed"));
      setCreatingChangeSet(false);
    }
  }

  async function researchNode(node: DocumentGraphNode) {
    setResearchingNodeId(node.id);
    setActionError(null);
    try {
      const result = await researchDocumentGraph(id, { nodeIds: [node.id] });
      setSelected(result.graph.nodes.find((item) => item.id === node.id) ?? node);
      await graph.refetch();
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : t("actionFailed"));
    } finally {
      setResearchingNodeId(null);
    }
  }

  async function researchGraphAndPrepare() {
    setResearchingGraph(true);
    setActionError(null);
    try {
      const result = await researchDocumentGraph(id, { createChangeSet: true });
      if (!result.change_set) throw new Error(t("actionFailed"));
      window.location.assign(`/graph/changes/${result.change_set.id}`);
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : t("actionFailed"));
      setResearchingGraph(false);
    }
  }

  async function refreshDocumentEditor() {
    await Promise.all([workspace.refetch(), content.refetch()]);
  }

  if (workspace.isLoading) return <div className="table-state page-loading"><span className="spinner" />{t("loading")}</div>;
  if (!workspace.data) return <div className="card table-state"><strong className="error">{t("documentNotFound")}</strong><Link className="button-link" href="/documents">{t("backToDocuments")}</Link></div>;
  const item = workspace.data;
  const evaluation = item.evaluation;
  const binaryOriginal = item.mime_type === "application/pdf"
    || item.mime_type.includes("wordprocessingml.document");

  return (
    <>
      <Link className="back-link" href="/documents">← {t("backToDocuments")}</Link>
      <header className="page-header">
        <div>
          <p className="eyebrow">{t("documentGraph")}</p>
          <h1>{item.filename}</h1>
          <div className="detail-meta">
            <StatusBadge status={item.processing_status} />
            <span className="tag">{item.extracted_char_count.toLocaleString("vi-VN")} {t("characters")}</span>
            <span className="tag">{item.graph_node_count} {t("nodes")}</span>
            <span className="tag">{item.graph_edge_count} {t("edges")}</span>
          </div>
        </div>
        <div className="actions detail-actions">
          {can("researcher") && <Link className="button-link secondary" href={`/chat?scope_type=document&scope_id=${id}`}>{t("brainstormDocument")}</Link>}
          {can("researcher") && item.processing_status === "needs_review" && item.graph_node_count > 0 && (
            <button onClick={researchGraphAndPrepare} disabled={researchingGraph}>
              {researchingGraph ? t("preparingKnowledgeGraph") : t("researchGraphAndPrepare")}
            </button>
          )}
          {can("researcher") && item.processing_status === "needs_review" && item.graph_node_count > 0 && (
            <button onClick={createChangeSet} disabled={creatingChangeSet}>
              {creatingChangeSet ? t("creatingChangeSet") : t("createChangeSet")}
            </button>
          )}
          {can("researcher") && item.processing_status === "failed" && <button onClick={retry}>{t("retry")}</button>}
          <a className="button-link secondary" href={`${API_URL}/documents/${id}/download`}>
            {t(binaryOriginal ? "downloadOriginal" : "download")}
          </a>
          <Link className="button-link secondary" href={`/research/${item.research_id}`}>{t("openResearch")}</Link>
        </div>
      </header>
      {actionError && <p className="notice error-notice">{actionError}</p>}
      {item.error_message && <p className="notice error-notice"><strong>{item.error_code}</strong> — {vietnameseApiErrorMessage(item.error_code)}</p>}

      {content.data && content.data.editable && user ? (
        <DocumentAIEditor
          workspace={item}
          content={content.data}
          userId={user.id}
          canEdit={can("researcher")}
          onChanged={refreshDocumentEditor}
        />
      ) : content.data ? <DocumentSourceViewer content={content.data} /> : null}
      {content.isLoading && <div className="card table-state"><span className="spinner" />{t("loadingDocumentContent")}</div>}
      {content.error && <p className="notice error-notice">{t("documentContentFailed")}</p>}

      <section className="document-analysis-grid">
        <article className="card paper-fit-panel">
          <p className="eyebrow">{t("paperFitEvaluation")}</p>
          {evaluation ? (
            <>
              <div className="paper-fit-score">
                <strong>{evaluation.fit_score ?? "—"}</strong>
                <div><span>{t("fitScore")}</span><StatusBadge status={evaluation.decision} /></div>
              </div>
              <p className="muted">{evaluation.reasoning_summary}</p>
              <div className="dimension-list">
                {Object.entries(evaluation.dimension_scores).map(([name, score]) => (
                  <div key={name}>
                    <span>{name.replaceAll("_", " ")}</span>
                    <div><i style={{ width: `${score}%` }} /></div><strong>{score}</strong>
                  </div>
                ))}
              </div>
              <div className="paper-fit-tags">
                {evaluation.matched_pillars.map((pillar) => <span className="tag" key={pillar}>{pillar}</span>)}
              </div>
              {evaluation.failed_gates.length > 0 && <p className="notice error-notice">{t("failedGates")}: {evaluation.failed_gates.map((gate) => t(`gate.${gate}`)).join(", ")}</p>}
            </>
          ) : <div className="table-state"><span className="spinner" />{t("evaluationPending")}</div>}
        </article>

        <article className="card document-limitations-panel">
          <p className="eyebrow">{t("processingProvenance")}</p>
          <dl>
            <div><dt>{t("provider")}</dt><dd>{item.provider_name ?? "—"}</dd></div>
            <div><dt>{t("model")}</dt><dd>{item.model_name ?? "—"}</dd></div>
            <div><dt>{t("attempts")}</dt><dd>{item.attempt_count}</dd></div>
            <div><dt>SHA-256</dt><dd>{item.content_hash}</dd></div>
          </dl>
          <h3>{t("limitations")}</h3>
          {item.extraction_limitations.length ? <ul>{item.extraction_limitations.map((limitation, index) => {
            const code = String(limitation.code ?? "");
            const translated = code ? t(`error.${code}`) : "";
            return <li key={index}>{translated && translated !== `error.${code}` ? translated : t("unknownLimitation")}</li>;
          })}</ul> : <p className="muted">{t("noLimitations")}</p>}
        </article>
      </section>

      <section className="card document-graph-panel" id="document-analysis">
        <div className="section-heading compact"><div><p className="eyebrow">{t("isolatedWorkspace")}</p><h2>{t("documentGraph")}</h2></div></div>
        {graph.data?.nodes.length ? (
          <div className="document-graph-layout">
            <DocumentGraphCanvas graph={graph.data} selectedId={selected?.id ?? null} onSelect={setSelected} />
            <aside className="document-node-inspector">
              {selected ? <>
                <p className="eyebrow">{selected.node_type}</p>
                <h3>{selected.label}</h3>
                <h4>{t("sourceGroundedSummary")}</h4>
                <p data-testid="document-node-summary">{selected.summary}</p>
                <StatusBadge status={selected.evidence_status} />
                <div className="document-node-ai-research">
                  <h4>{t("aiIndependentResearch")}</h4>
                  {selected.ai_research ? <>
                    <p>{selected.ai_research.research_summary}</p>
                    <div className="document-node-comparison">
                      <strong>{t("comparison")}</strong>
                      <span className={`tag comparison-${selected.ai_research.comparison_status}`}>
                        {t(comparisonTranslation[selected.ai_research.comparison_status])}
                      </span>
                    </div>
                    {selected.ai_research.difference_summary && (
                      <p className="notice warning-notice">{selected.ai_research.difference_summary}</p>
                    )}
                    <small className="muted">
                      {selected.ai_research.provider_name} · {selected.ai_research.model_name}
                    </small>
                  </> : <p className="muted">{t("aiResearchPending")}</p>}
                  {can("researcher") && !["document", "section"].includes(selected.node_type) && (
                    <button
                      className="secondary"
                      onClick={() => researchNode(selected)}
                      disabled={researchingNodeId === selected.id}
                    >
                      {researchingNodeId === selected.id
                        ? t("researchingWithAi")
                        : t("researchNodeWithAi")}
                    </button>
                  )}
                </div>
                <h4>{t("evidence")}</h4>
                {selected.evidence.length
                  ? selected.evidence.map((evidence) => <blockquote key={evidence.id}>{evidence.excerpt}<small>{String(evidence.location.section_heading ?? evidence.location.page ?? "")}</small></blockquote>)
                  : <p className="muted">{t("evidencePending")}</p>}
              </> : <div className="table-state"><strong>{t("selectDocumentNode")}</strong></div>}
            </aside>
          </div>
        ) : <div className="table-state"><strong>{activeStatuses.includes(item.processing_status) ? t("graphProcessing") : t("noDocumentGraph")}</strong></div>}
      </section>
    </>
  );
}
