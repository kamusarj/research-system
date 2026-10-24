"use client";

import type { GraphLayoutMode } from "@/lib/knowledge-graph/types";

type Props = {
  layout: GraphLayoutMode;
  search: string;
  onLayoutChange: (layout: GraphLayoutMode) => void;
  onSearch: (value: string) => void;
  onFit: () => void;
  onReset: () => void;
  onRelayout: () => void;
  explorerOpen: boolean;
  onToggleExplorer: () => void;
  labelsVisible: boolean;
  onToggleLabels: () => void;
  labels: {
    search: string;
    fit: string;
    reset: string;
    relayout: string;
    relationship: string;
    hierarchy: string;
    orbit: string;
    explorer: string;
    labels: string;
  };
};

export function GraphToolbar({
  layout,
  search,
  onLayoutChange,
  onSearch,
  onFit,
  onReset,
  onRelayout,
  explorerOpen,
  onToggleExplorer,
  labelsVisible,
  onToggleLabels,
  labels,
}: Props) {
  return (
    <div className="graph-toolbar">
      <div className="graph-toolbar-search">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
        <input
          value={search}
          onChange={(event) => onSearch(event.target.value)}
          placeholder={labels.search}
          aria-label={labels.search}
        />
      </div>
      <div className="graph-view-switcher" role="group" aria-label="Bố cục đồ thị">
        <button
          className={layout === "relationship" ? "active" : ""}
          onClick={() => onLayoutChange("relationship")}
          aria-pressed={layout === "relationship"}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><circle cx="5" cy="7" r="2"/><circle cx="19" cy="6" r="2"/><circle cx="12" cy="18" r="2"/><path d="m7 8 4 8m6-9-4 9M7 7l10-1"/></svg>
          {labels.relationship}
        </button>
        <button
          className={layout === "hierarchy" ? "active" : ""}
          onClick={() => onLayoutChange("hierarchy")}
          aria-pressed={layout === "hierarchy"}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M4 4v6h6M20 4v6h-6M12 10v10M6 20h12"/></svg>
          {labels.hierarchy}
        </button>
        <button
          className={layout === "orbit" ? "active" : ""}
          onClick={() => onLayoutChange("orbit")}
          aria-pressed={layout === "orbit"}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><circle cx="12" cy="12" r="2"/><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="10"/></svg>
          {labels.orbit}
        </button>
      </div>
      <div className="graph-toolbar-actions">
        <button
          className={`graph-toolbar-btn secondary graph-explorer-toggle ${explorerOpen ? "active" : ""}`}
          onClick={onToggleExplorer}
          aria-pressed={explorerOpen}
          title={labels.explorer}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M4 5h16M7 12h10M10 19h4" />
          </svg>
          <span>{labels.explorer}</span>
        </button>
        <button
          className={`graph-toolbar-btn secondary ${labelsVisible ? "active" : ""}`}
          onClick={onToggleLabels}
          aria-pressed={labelsVisible}
          title={labels.labels}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M9 18h6M10 22h4M8.5 14.5A7 7 0 1 1 15.5 14.5C14.4 15.4 14 16 14 18h-4c0-2-.4-2.6-1.5-3.5Z" />
          </svg>
          <span>{labels.labels}</span>
        </button>
        <button className="graph-toolbar-btn secondary" onClick={onFit} title={labels.fit}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
          </svg>
          <span>{labels.fit}</span>
        </button>
        <button className="graph-toolbar-btn secondary" onClick={onRelayout} title={labels.relayout}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M21 2v6h-6M3 12a9 9 0 0 1 15-6.7L21 8M3 22v-6h6M21 12a9 9 0 0 1-15 6.7L3 16" />
          </svg>
          <span>{labels.relayout}</span>
        </button>
        <button className="graph-toolbar-btn secondary" onClick={onReset} title={labels.reset}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
            <path d="M3 3v5h5" />
          </svg>
          <span>{labels.reset}</span>
        </button>
      </div>
    </div>
  );
}
