"use client";

import type { GraphFilters as FilterState } from "@/lib/knowledge-graph/types";

type Props = {
  filters: FilterState;
  nodeTypes: string[];
  onChange: (filters: FilterState) => void;
  labels: { filters: string; nodeTypes: string; sources: string; confidence: string; time: string };
};

const sourceTypes = ["github", "article", "facebook_reel", "pdf", "rss"];

export function GraphFilters({ filters, nodeTypes, onChange, labels }: Props) {
  function toggle(key: "nodeTypes" | "sourceTypes", value: string) {
    const values = filters[key];
    onChange({
      ...filters,
      [key]: values.includes(value) ? values.filter((item) => item !== value) : [...values, value],
    });
  }
  return (
    <section className="graph-filter-panel">
      <h3>{labels.filters}</h3>
      <p className="filter-label">{labels.nodeTypes}</p>
      <div className="filter-checks">
        {nodeTypes.map((type) => (
          <label key={type}>
            <input
              type="checkbox"
              checked={filters.nodeTypes.includes(type)}
              onChange={() => toggle("nodeTypes", type)}
            />
            <span>{type}</span>
          </label>
        ))}
      </div>
      <p className="filter-label">{labels.sources}</p>
      <div className="filter-checks compact">
        {sourceTypes.map((type) => (
          <label key={type}>
            <input
              type="checkbox"
              checked={filters.sourceTypes.includes(type)}
              onChange={() => toggle("sourceTypes", type)}
            />
            <span>{type.replace("_", " ")}</span>
          </label>
        ))}
      </div>
      <label className="range-filter">
        <span>{labels.confidence}: {Math.round(filters.minConfidence * 100)}%</span>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={filters.minConfidence}
          onChange={(event) => onChange({ ...filters, minConfidence: Number(event.target.value) })}
        />
      </label>
      <p className="filter-label">{labels.time}</p>
      <div className="date-filters">
        <input
          type="date"
          value={filters.dateFrom}
          onChange={(event) => onChange({ ...filters, dateFrom: event.target.value })}
        />
        <input
          type="date"
          value={filters.dateTo}
          onChange={(event) => onChange({ ...filters, dateTo: event.target.value })}
        />
      </div>
    </section>
  );
}
