"use client";

import { useState } from "react";
import { useI18n } from "@/lib/i18n";
import { fallbackGraphColor, graphColors, graphTypeLabel } from "@/lib/knowledge-graph/graph-theme";

export function GraphLegend({ counts }: { counts: Record<string, number> }) {
  const { t } = useI18n();
  const [expanded, setExpanded] = useState(true);
  const totalNodes = Object.values(counts).reduce((sum, count) => sum + count, 0);
  // Both graph views share this component, so a label has to resolve from either
  // vocabulary and fall back to a readable form rather than a raw type identifier.
  const label = (type: string) => {
    const key = `nodeType.${type}`;
    const translated = t(key);
    return translated === key ? graphTypeLabel(type) : translated;
  };

  return (
    <section className="graph-legend card">
      <button
        className="graph-legend-header"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        <span className="graph-legend-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <line x1="3" y1="9" x2="21" y2="9" />
            <line x1="9" y1="21" x2="9" y2="9" />
          </svg>
          {t("legend")}
          <span className="graph-legend-count">{totalNodes}</span>
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
          className={`graph-legend-chevron ${expanded ? "expanded" : ""}`}
          aria-hidden="true"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      {expanded && (
        <div className="graph-legend-items">
          {Object.entries(counts).map(([type, count]) => (
            <div key={type} className="graph-legend-item">
              <i
                className="graph-legend-dot"
                style={{ background: graphColors[type] ?? fallbackGraphColor }}
              />
              <span className="graph-legend-label">{label(type)}</span>
              <span className="graph-legend-value">{count}</span>
            </div>
          ))}
          {totalNodes === 0 && <p className="muted">{t("legendEmpty")}</p>}
        </div>
      )}
    </section>
  );
}
