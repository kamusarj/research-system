import type { GraphEvidence } from "@/lib/knowledge-graph/types";

export function EvidenceList({ evidence }: { evidence: GraphEvidence[] }) {
  if (!evidence.length) return <p className="muted">Chưa có bằng chứng liên kết.</p>;
  return (
    <div className="evidence-list">
      {evidence.map((item, index) => (
        <blockquote key={`${item.location ?? item.timestamp_seconds ?? "evidence"}-${index}`}>
          <p>{item.text ?? "Tham chiếu bằng chứng"}</p>
          <small>
            {item.section && `${item.section} · `}
            {item.page != null && `trang ${item.page} · `}
            {item.timestamp_seconds != null && `${item.timestamp_seconds}s · `}
            {item.location}
          </small>
        </blockquote>
      ))}
    </div>
  );
}
