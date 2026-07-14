import { EvidenceList } from "./evidence-list";
import type { GraphEdge, GraphNode } from "@/lib/knowledge-graph/types";

export function EdgeDetailsPanel({
  edge,
  source,
  target,
}: {
  edge: GraphEdge;
  source?: GraphNode;
  target?: GraphNode;
}) {
  return (
    <div className="card detail-panel" data-testid="edge-details">
      <p className="eyebrow">Relationship</p>
      <h2>{edge.type}</h2>
      <p>{source?.label ?? edge.source} → {target?.label ?? edge.target}</p>
      <dl>
        <div><dt>Confidence</dt><dd>{Math.round(edge.confidence * 100)}%</dd></div>
        <div><dt>Evidence</dt><dd>{edge.evidence_count}</dd></div>
      </dl>
      <h3>Evidence</h3>
      <EvidenceList evidence={edge.evidence} />
    </div>
  );
}
