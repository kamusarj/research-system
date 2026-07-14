import Link from "next/link";
import { fallbackGraphColor, graphColors } from "@/lib/knowledge-graph/graph-theme";
import type { GraphEdge, GraphNode } from "@/lib/knowledge-graph/types";

type Props = {
  node: GraphNode;
  relationships: GraphEdge[];
  expanding: boolean;
  onExpand: () => void;
  onHide: () => void;
};

export function NodeDetailsPanel({ node, relationships, expanding, onExpand, onHide }: Props) {
  return (
    <div className="card detail-panel" data-testid="node-details">
      <span
        className="node-dot"
        style={{ background: graphColors[node.type] ?? fallbackGraphColor }}
      />
      <p className="eyebrow">{node.type}</p>
      <h2>{node.label}</h2>
      <p className="muted">{node.summary || "No summary is available yet."}</p>
      <dl>
        <div><dt>Confidence</dt><dd>{Math.round(node.confidence * 100)}%</dd></div>
        <div><dt>Sources</dt><dd>{node.source_count}</dd></div>
        <div><dt>Relationships</dt><dd>{relationships.length}</dd></div>
      </dl>
      <div className="actions wrap">
        <button onClick={onExpand} disabled={expanding}>{expanding ? "Expanding…" : "Expand neighbors"}</button>
        <button className="secondary" onClick={onHide}>Hide node</button>
      </div>
      {node.type === "ResearchItem" && (
        <Link className="button-link" href={`/research/${node.id}`}>Open research</Link>
      )}
      {node.source_url && (
        <a className="source-link" href={node.source_url} target="_blank" rel="noreferrer">
          Open original source ↗
        </a>
      )}
      <h3>Relationships</h3>
      {relationships.slice(0, 10).map((edge) => (
        <p className="relationship-row" key={edge.id}>
          <strong>{edge.type}</strong> · {Math.round(edge.confidence * 100)}%
        </p>
      ))}
      {!relationships.length && <p className="muted">No visible relationships.</p>}
    </div>
  );
}
