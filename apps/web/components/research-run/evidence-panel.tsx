"use client";

import { PERSPECTIVE_LABELS, type ResearchRunClaim, type ResearchRunSource } from "@/lib/research-runs";

type Citation = { source: ResearchRunSource; claims: ResearchRunClaim[] };

export function EvidencePanel({
  citations,
  active,
  onSelect,
}: {
  citations: Map<number, Citation>;
  active: number | null;
  onSelect: (citation: number) => void;
}) {
  const numbers = [...citations.keys()].sort((a, b) => a - b);
  const selected = active !== null ? citations.get(active) : undefined;
  if (numbers.length === 0) return null;
  return (
    <aside className="evidence-panel" aria-label="Nguồn và trích dẫn">
      <h2>Nguồn đã trích dẫn</h2>
      <ol className="evidence-index">
        {numbers.map((number) => {
          const { source } = citations.get(number)!;
          return (
            <li key={number}>
              <button
                type="button"
                className={`evidence-chip${number === active ? " active" : ""}`}
                aria-pressed={number === active}
                onClick={() => onSelect(number)}
              >
                <span className="evidence-number">{number}</span>
                <span className="evidence-title">{source.title || source.domain}</span>
              </button>
            </li>
          );
        })}
      </ol>
      {selected ? (
        <div className="evidence-detail" aria-live="polite">
          <p className="evidence-meta">
            <span className="citation static">{active}</span>
            {selected.source.provider === "internal_kb" ? "Kho nghiên cứu nội bộ" : selected.source.domain}
            <span className="evidence-perspective">{PERSPECTIVE_LABELS[selected.source.perspective]}</span>
          </p>
          <a className="evidence-link" href={selected.source.url} target={selected.source.url.startsWith("/") ? undefined : "_blank"} rel="noreferrer">
            {selected.source.title || selected.source.url}
          </a>
          {selected.source.suspicious && (
            <p className="notice warning-notice">Trang này chứa đoạn văn cố điều khiển AI; mọi nhận định từ nó đã qua bước kiểm tra suy luận.</p>
          )}
          <ul className="evidence-quotes">
            {selected.claims.map((claim) => (
              <li key={claim.id}>
                <p className="evidence-claim">{claim.text}</p>
                <blockquote lang="und">{claim.matched_quote ?? claim.quote}</blockquote>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="muted evidence-hint">Chọn một số trích dẫn trong báo cáo để xem câu gốc trong nguồn.</p>
      )}
    </aside>
  );
}
