import { EvidenceList } from "./evidence-list";
import { graphRelationshipLabel } from "@/lib/knowledge-graph/graph-theme";
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
      <p className="eyebrow">Mối quan hệ</p>
      <h2>{graphRelationshipLabel(edge.type)}</h2>
      <p>{source?.label ?? edge.source} → {target?.label ?? edge.target}</p>
      <dl>
        <div><dt>Độ tin cậy</dt><dd>{Math.round(edge.confidence * 100)}%</dd></div>
        <div><dt>Bằng chứng</dt><dd>{edge.evidence_count}</dd></div>
      </dl>
      <h3>Bằng chứng</h3>
      <EvidenceList evidence={edge.evidence} />
    </div>
  );
}
