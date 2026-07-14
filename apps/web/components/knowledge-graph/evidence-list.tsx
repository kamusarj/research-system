import type { GraphEvidence } from "@/lib/knowledge-graph/types";

export function EvidenceList({ evidence }: { evidence: GraphEvidence[] }) {
  if (!evidence.length) return <p className="muted">No linked evidence is available yet.</p>;
  return (
    <div className="evidence-list">
      {evidence.map((item, index) => (
        <blockquote key={`${item.location ?? item.timestamp_seconds ?? "evidence"}-${index}`}>
          <p>{item.text ?? "Evidence reference"}</p>
          <small>
            {item.section && `${item.section} · `}
            {item.page != null && `page ${item.page} · `}
            {item.timestamp_seconds != null && `${item.timestamp_seconds}s · `}
            {item.location}
          </small>
        </blockquote>
      ))}
    </div>
  );
}
