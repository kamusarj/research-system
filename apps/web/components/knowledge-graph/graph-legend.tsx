"use client";

import { fallbackGraphColor, graphColors } from "@/lib/knowledge-graph/graph-theme";

export function GraphLegend({ counts }: { counts: Record<string, number> }) {
  return (
    <section className="graph-legend card">
      <h3>Legend</h3>
      {Object.entries(counts).map(([type, count]) => (
        <div key={type}>
          <i style={{ background: graphColors[type] ?? fallbackGraphColor }} />
          <span>{type}</span>
          <strong>{count}</strong>
        </div>
      ))}
    </section>
  );
}
