"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { EvidencePanel } from "@/components/research-run/evidence-panel";
import { RunProgress } from "@/components/research-run/run-progress";
import { ReportMarkdown } from "@/components/report-markdown";
import { API_URL, api } from "@/lib/api";
import {
  citationIndex,
  isTerminal,
  RUN_STATUS_LABELS,
  subscribeRunEvents,
  type ResearchRunDetail,
  type ResearchRunEvent,
} from "@/lib/research-runs";

const REJECTION_LABELS: Record<string, string> = {
  quote_not_found: "trích dẫn không có trong nguồn",
  quote_too_short: "trích dẫn quá ngắn",
  number_not_in_quote: "số liệu không có trong trích dẫn",
  not_supported: "nguồn không ủng hộ nhận định",
  partial_support: "nguồn chỉ ủng hộ một phần",
};

export default function ResearchRunPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [polling, setPolling] = useState(false);
  const [liveEvents, setLiveEvents] = useState<ResearchRunEvent[]>([]);
  const [activeCitation, setActiveCitation] = useState<number | null>(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const queryKey = useMemo(() => ["research-run", id], [id]);
  const detail = useQuery({
    queryKey,
    queryFn: () => api<ResearchRunDetail>(`/research-runs/${id}`),
    refetchInterval: (query) => (polling && query.state.data && !isTerminal(query.state.data.status) ? 3000 : false),
  });
  const run = detail.data;
  const terminal = run ? isTerminal(run.status) : false;

  const events = useMemo(() => {
    const merged = new Map<number, ResearchRunEvent>();
    for (const event of [...(run?.events ?? []), ...liveEvents]) merged.set(event.id, event);
    return [...merged.values()].sort((a, b) => a.id - b.id);
  }, [run?.events, liveEvents]);
  const lastEventId = run?.events.at(-1)?.id ?? 0;

  useEffect(() => {
    if (!run || terminal || polling) return;
    return subscribeRunEvents(id, lastEventId, {
      onEvent: (event) => {
        setLiveEvents((current) => [...current, event]);
        if (event.kind !== "progress") void queryClient.invalidateQueries({ queryKey });
      },
      onEnd: () => void queryClient.invalidateQueries({ queryKey }),
      onUnavailable: () => setPolling(true),
    });
    // Chỉ mở lại luồng khi đổi lượt chạy hoặc trạng thái kết thúc; sự kiện mới đến qua chính luồng này.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, terminal, polling, Boolean(run)]);

  const citations = useMemo(() => (run ? citationIndex(run) : new Map()), [run]);

  async function act(path: string, done: string) {
    setBusy(true);
    setStatus("");
    try {
      await api(`/research-runs/${id}/${path}`, { method: "POST" });
      setLiveEvents([]);
      setPolling(false);
      await queryClient.invalidateQueries({ queryKey });
      setStatus(done);
    } catch (reason) {
      setStatus(reason instanceof Error ? reason.message : "Không thể thực hiện thao tác.");
    } finally {
      setBusy(false);
    }
  }

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setStatus("Đã sao chép liên kết tới lượt nghiên cứu.");
    } catch {
      setStatus("Không sao chép được; hãy sao chép địa chỉ trên thanh trình duyệt.");
    }
  }

  if (detail.isLoading) return <div className="deep-research"><div className="skeleton skeleton-line" /><div className="skeleton skeleton-block" /></div>;
  if (detail.error || !run) return <p className="notice error-notice" role="alert">{detail.error?.message ?? "Không tìm thấy lượt nghiên cứu."}</p>;

  const rejected = run.claims.filter((claim) => claim.status === "rejected" || claim.status === "flagged");
  const reasons = rejected.reduce<Record<string, number>>((all, claim) => {
    const key = claim.reason ?? "khác";
    all[key] = (all[key] ?? 0) + 1;
    return all;
  }, {});

  return (
    <div className="deep-research run-page">
      <nav className="breadcrumb" aria-label="Đường dẫn"><Link href="/research/new">Nghiên cứu sâu</Link><span aria-hidden="true">/</span><span>Lượt nghiên cứu</span></nav>
      <header className="run-header">
        <span className={`run-status ${run.status}`}>{RUN_STATUS_LABELS[run.status]}</span>
        <h1>{run.question}</h1>
        <div className="run-actions">
          {!terminal && <button type="button" className="secondary" disabled={busy} onClick={() => void act("cancel", "Đã gửi yêu cầu hủy.")}>Hủy</button>}
          {run.status === "failed" && <button type="button" disabled={busy} onClick={() => void act("retry", "Đã xếp hàng chạy lại.")}>Chạy lại từ bước lỗi</button>}
          <button type="button" className="secondary" onClick={() => void copyLink()}>Sao chép liên kết</button>
          {run.report_markdown && <a className="secondary-link" href={`${API_URL}/research-runs/${run.id}/export.md`} download>Tải Markdown</a>}
          {run.report_research_id && <Link className="button-link" href={`/research/${run.report_research_id}`}>Mở bản nháp để duyệt</Link>}
        </div>
        {status && <p className="run-action-status" role="status">{status}</p>}
      </header>

      <RunProgress run={run} events={events} />

      {run.status === "failed" && (
        <p className="notice error-notice" role="alert">{run.error_message ?? "Lượt nghiên cứu thất bại."} Kết quả đã có vẫn được giữ.</p>
      )}

      <div className="run-body">
        <article className="card report-card" aria-busy={!terminal}>
          {run.report_markdown ? (
            <ReportMarkdown content={run.report_markdown} onCite={setActiveCitation} activeCitation={activeCitation} />
          ) : terminal ? (
            <p className="muted">Không có báo cáo cho lượt này.</p>
          ) : (
            <div className="report-placeholder" aria-label="Báo cáo đang được chuẩn bị">
              <div className="skeleton skeleton-line short" />
              <div className="skeleton skeleton-line" />
              <div className="skeleton skeleton-line" />
              <div className="skeleton skeleton-line short" />
              <p className="muted">Báo cáo sẽ hiện ở đây khi kiểm chứng xong.</p>
            </div>
          )}
        </article>
        <EvidencePanel citations={citations} active={activeCitation} onSelect={setActiveCitation} />
      </div>

      {run.claims.length > 0 && (
        <details className="card run-audit">
          <summary>Chi tiết kiểm chứng: {run.claims.filter((c) => c.status === "verified").length} nhận định đạt, {rejected.length} bị loại hoặc gắn cờ</summary>
          <ul>
            {Object.entries(reasons).map(([reason, total]) => <li key={reason}>{total} — {REJECTION_LABELS[reason] ?? reason}</li>)}
          </ul>
          <h3>Nguồn đã xét</h3>
          <ul className="run-source-list">
            {run.sources.map((source) => (
              <li key={source.id}>
                <span className={`source-state ${source.status}`}>{source.citation_index ? `[${source.citation_index}]` : source.status}</span>
                <a href={source.url} target={source.url.startsWith("/") ? undefined : "_blank"} rel="noreferrer">{source.title || source.url}</a>
                <span className="muted">{source.domain}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
