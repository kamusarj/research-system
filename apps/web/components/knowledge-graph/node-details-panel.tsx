"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { EvidenceList } from "@/components/knowledge-graph/evidence-list";
import { useOntologyNode } from "@/hooks/use-ontology-node";
import { useI18n } from "@/lib/i18n";
import { fallbackGraphColor, graphColors, graphRelationshipLabel, graphTypeLabel } from "@/lib/knowledge-graph/graph-theme";
import type { GraphEdge, GraphNode, GraphView } from "@/lib/knowledge-graph/types";

type DetailTab = "overview" | "children" | "evidence" | "provenance";

type Props = {
  node: GraphNode;
  relationships: GraphEdge[];
  childNodes?: GraphNode[];
  ontologyBacked?: boolean;
  view: GraphView;
  inCurrentView: boolean;
  expanding: boolean;
  onExpand: () => void;
  onHide: () => void;
  onBrowseNode: (nodeId: string) => void;
};

export function NodeDetailsPanel({
  node,
  relationships,
  childNodes = [],
  ontologyBacked = false,
  view,
  inCurrentView,
  expanding,
  onExpand,
  onHide,
  onBrowseNode,
}: Props) {
  const { t } = useI18n();
  const [tab, setTab] = useState<DetailTab>("overview");
  const ontology = useOntologyNode(
    node.id,
    ontologyBacked && view === "hierarchy" && inCurrentView,
  );
  const evidence = useMemo(
    () => relationships.flatMap((relationship) => relationship.evidence),
    [relationships],
  );
  const provenance = Object.entries(node.provenance ?? {});

  return (
    <div className="card detail-panel" data-testid="node-details">
      <div className="detail-panel-header">
        <div className="detail-panel-type">
          <span
            className="node-dot"
            style={{ background: graphColors[node.type] ?? fallbackGraphColor }}
          />
          <span className="eyebrow">{graphTypeLabel(node.type)}</span>
        </div>
        <div className="detail-panel-actions">
          {view === "relationship" && (
            <button
              className="icon-btn"
              onClick={onExpand}
              disabled={expanding}
              title={t("expandNeighbors")}
              aria-label={t("expandNeighbors")}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
              </svg>
            </button>
          )}
          {view === "hierarchy" && inCurrentView && (node.child_count ?? 0) > 0 && (
            <button
              className="icon-btn"
              onClick={() => onBrowseNode(node.id)}
              title={t("browseBranch")}
              aria-label={t("browseBranch")}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3v6M5 21v-6h14v6M5 15v-3h14v3" />
              </svg>
            </button>
          )}
          <button
            className="icon-btn secondary"
            onClick={onHide}
            title={t("hideNode")}
            aria-label={t("hideNode")}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
              <circle cx="12" cy="12" r="3" />
              <line x1="2" y1="2" x2="22" y2="22" />
            </svg>
          </button>
        </div>
      </div>

      <h2 className="detail-panel-title">{node.label}</h2>
      <p className="detail-panel-summary muted">{node.summary || t("noSummary")}</p>

      <div className="detail-tabs" role="tablist" aria-label={t("nodeDetails")}>
        {(["overview", "children", "evidence", "provenance"] as DetailTab[]).map((item) => (
          <button
            key={item}
            role="tab"
            aria-selected={tab === item}
            className={tab === item ? "active" : ""}
            onClick={() => setTab(item)}
          >
            {t(`detailTab.${item}`)}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="detail-tab-content">
          <div className="detail-stats">
            <div className="detail-stat">
              <span className="detail-stat-label">{t("confidence")}</span>
              <span className="detail-stat-value">{Math.round(node.confidence * 100)}%</span>
            </div>
            <div className="detail-stat">
              <span className="detail-stat-label">{t("sources")}</span>
              <span className="detail-stat-value">{node.source_count}</span>
            </div>
            <div className="detail-stat">
              <span className="detail-stat-label">{t("relationships")}</span>
              <span className="detail-stat-value">{relationships.length}</span>
            </div>
          </div>

          <div className="detail-links">
            {view === "hierarchy" && (
              <Link className="detail-link primary" href={`/chat?scope_type=node&scope_id=${node.id}`}>
                {t("includeInChat")}
              </Link>
            )}
            {node.type === "ResearchItem" && (
              <Link className="detail-link primary" href={`/research/${node.id}`}>
                {t("openResearch")}
              </Link>
            )}
            {node.source_url && (
              <a className="detail-link" href={node.source_url} target="_blank" rel="noreferrer">
                {t("openOriginalSource")}
              </a>
            )}
          </div>

          {relationships.length > 0 && (
            <div className="detail-relationships">
              <h3 className="detail-relationships-title">{t("relationships")}</h3>
              <div className="detail-relationships-list">
                {relationships.slice(0, 8).map((edge) => (
                  <div className="detail-relationship-item" key={edge.id}>
                    <span className="detail-relationship-type">{graphRelationshipLabel(edge.type)}</span>
                    <span className="detail-relationship-confidence">
                      {Math.round(edge.confidence * 100)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === "children" && (
        <div className="detail-tab-content hierarchy-child-list">
          {(view !== "hierarchy" || !inCurrentView) && (
            <p className="muted">
              {view === "hierarchy" ? t("selectionOutsideView") : t("childrenHierarchyOnly")}
            </p>
          )}
          {ontologyBacked && view === "hierarchy" && inCurrentView && ontology.children.isLoading && <p className="muted">{t("loading")}</p>}
          {ontologyBacked && view === "hierarchy" && inCurrentView && ontology.children.error && (
            <p className="error">{t("childrenLoadFailed")}</p>
          )}
          {view === "hierarchy" && inCurrentView && (
            ontologyBacked ? ontology.children.data?.length === 0 : childNodes.length === 0
          ) && (
            <p className="muted">{t("noChildNodes")}</p>
          )}
          {ontologyBacked && view === "hierarchy" && inCurrentView && ontology.children.data?.map((child) => (
            <button key={child.id} onClick={() => onBrowseNode(child.id)}>
              <span>{child.canonical_label}</span>
              <strong>{child.child_count}</strong>
            </button>
          ))}
          {!ontologyBacked && view === "hierarchy" && inCurrentView && childNodes.map((child) => (
            <button key={child.id} onClick={() => onBrowseNode(child.id)}>
              <span>{child.label}</span>
              <strong>{child.child_count ?? 0}</strong>
            </button>
          ))}
        </div>
      )}

      {tab === "evidence" && (
        <div className="detail-tab-content">
          <p className="detail-count-line">
            {node.evidence_count ?? evidence.length} {t("evidenceItems")}
          </p>
          {evidence.length > 0 ? <EvidenceList evidence={evidence} /> : <p className="muted">{t("noEvidence")}</p>}
        </div>
      )}

      {tab === "provenance" && (
        <div className="detail-tab-content provenance-list">
          <div><span>{t("lifecycle")}</span><strong>{t(`status.${node.lifecycle_status ?? "approved"}`)}</strong></div>
          <div><span>{t("parentNode")}</span><strong>{node.primary_parent_id ?? t("none")}</strong></div>
          {provenance.map(([key, value]) => (
            <div key={key}><span>{key}</span><strong>{String(value || t("none"))}</strong></div>
          ))}
          {provenance.length === 0 && <p className="muted">{t("noProvenance")}</p>}
        </div>
      )}
    </div>
  );
}
