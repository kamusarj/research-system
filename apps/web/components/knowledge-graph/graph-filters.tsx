"use client";

import { useState } from "react";
import { graphTypeLabel } from "@/lib/knowledge-graph/graph-theme";
import type { GraphFilters as FilterState, GraphView } from "@/lib/knowledge-graph/types";

type Props = {
  filters: FilterState;
  nodeTypes: string[];
  view: GraphView;
  onChange: (filters: FilterState) => void;
  labels: { filters: string; nodeTypes: string; sources: string; confidence: string; time: string };
  typeLabels?: Record<string, string>;
};

const sourceTypes = ["github", "article", "facebook_reel", "pdf", "rss"];
const sourceTypeLabels: Record<string, string> = {
  github: "GitHub",
  article: "Bài viết",
  facebook_reel: "Facebook Reel",
  pdf: "PDF",
  rss: "RSS",
};

export function GraphFilters({ filters, nodeTypes, view, onChange, labels, typeLabels }: Props) {
  const [expanded, setExpanded] = useState(true);
  // Source type, confidence and collection date describe collected research items. The
  // hierarchy draws canonical ontology nodes, which have none of those, so offering the
  // controls there only invites a reader to filter everything away for no reason.
  const showResearchFilters = view === "relationship";

  function toggle(key: "nodeTypes" | "sourceTypes", value: string) {
    const values = filters[key];
    onChange({
      ...filters,
      [key]: values.includes(value) ? values.filter((item) => item !== value) : [...values, value],
    });
  }

  return (
    <section className="graph-filter-panel card">
      <button
        className="graph-filter-header"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        <span className="graph-filter-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
          </svg>
          {labels.filters}
        </span>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`graph-filter-chevron ${expanded ? "expanded" : ""}`}
          aria-hidden="true"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      {expanded && (
        <div className="graph-filter-content">
          <div className="filter-section">
            <p className="filter-label">{labels.nodeTypes}</p>
            <div className="filter-checks">
              {nodeTypes.map((type) => (
                <label key={type} className="filter-check-item">
                  <input
                    type="checkbox"
                    checked={filters.nodeTypes.includes(type)}
                    onChange={() => toggle("nodeTypes", type)}
                  />
                  <span className="filter-check-label">{graphTypeLabel(type, typeLabels)}</span>
                </label>
              ))}
            </div>
          </div>

          {showResearchFilters && (
          <div className="filter-section">
            <p className="filter-label">{labels.sources}</p>
            <div className="filter-checks">
              {sourceTypes.map((type) => (
                <label key={type} className="filter-check-item">
                  <input
                    type="checkbox"
                    checked={filters.sourceTypes.includes(type)}
                    onChange={() => toggle("sourceTypes", type)}
                  />
                  <span className="filter-check-label">{sourceTypeLabels[type] ?? type}</span>
                </label>
              ))}
            </div>
          </div>
          )}

          {showResearchFilters && (
          <div className="filter-section">
            <p className="filter-label">{labels.confidence}</p>
            <div className="range-filter">
              <div className="range-header">
                <span className="range-value">{Math.round(filters.minConfidence * 100)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={filters.minConfidence}
                onChange={(event) => onChange({ ...filters, minConfidence: Number(event.target.value) })}
              />
            </div>
          </div>
          )}

          {showResearchFilters && (
          <div className="filter-section">
            <p className="filter-label">{labels.time}</p>
            <div className="date-filters">
              <input
                type="date"
                value={filters.dateFrom}
                onChange={(event) => onChange({ ...filters, dateFrom: event.target.value })}
                placeholder="Từ ngày"
              />
              <input
                type="date"
                value={filters.dateTo}
                onChange={(event) => onChange({ ...filters, dateTo: event.target.value })}
                placeholder="Đến ngày"
              />
            </div>
          </div>
          )}
        </div>
      )}
    </section>
  );
}
