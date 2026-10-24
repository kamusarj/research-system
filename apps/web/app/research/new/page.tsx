"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent, type KeyboardEvent } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { PERSPECTIVE_LABELS, RUN_STATUS_LABELS, type ResearchRun } from "@/lib/research-runs";

const EXAMPLES = [
  "Doanh nghiệp vừa và nhỏ ở Việt Nam đang dùng AI agent cho chăm sóc khách hàng như thế nào?",
  "So sánh các nền tảng xây dựng AI agent cho doanh nghiệp: chi phí, tích hợp và quản trị.",
  "Những rủi ro tuân thủ khi triển khai AI agent xử lý dữ liệu khách hàng là gì?",
];

const dateFormat = new Intl.DateTimeFormat("vi-VN", { dateStyle: "short", timeStyle: "short" });

export default function NewResearchPage() {
  const router = useRouter();
  const { can } = useAuth();
  const [question, setQuestion] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const features = useQuery({
    queryKey: ["system-features"],
    queryFn: () => api<{ research_agent?: boolean }>("/system/features"),
    staleTime: 60_000,
  });
  const history = useQuery({
    queryKey: ["research-runs", "mine"],
    queryFn: () => api<{ items: ResearchRun[]; total: number }>("/research-runs?mine=true&page_size=10"),
  });
  const enabled = features.data?.research_agent === true;
  const canStart = enabled && can("researcher");
  const trimmed = question.trim();

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!canStart || trimmed.length < 10 || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const run = await api<ResearchRun>("/research-runs", { method: "POST", body: JSON.stringify({ question: trimmed }) });
      router.push(`/research/runs/${run.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể bắt đầu nghiên cứu.");
      setSubmitting(false);
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) void submit();
  }

  return (
    <div className="deep-research">
      <header className="page-header">
        <div>
          <h1>Nghiên cứu sâu</h1>
          <p className="page-description">
            Đặt một câu hỏi. Hệ thống tìm nguồn trên web và trong kho tri thức, đối chiếu từng nhận định với câu gốc
            trong nguồn, rồi viết báo cáo nháp mà mỗi câu đều dẫn được nguồn.
          </p>
        </div>
      </header>

      {features.isSuccess && !enabled && (
        <p className="notice" role="status">
          Nghiên cứu sâu chưa được bật trên máy chủ này. Quản trị viên cần đặt <code>RESEARCH_AGENT_ENABLED=true</code> và
          chạy dịch vụ tìm kiếm SearXNG (xem README).
        </p>
      )}

      <form className="card question-form" onSubmit={submit} aria-busy={submitting}>
        <label htmlFor="research-question">Câu hỏi nghiên cứu</label>
        <textarea
          id="research-question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={onKeyDown}
          rows={4}
          maxLength={1000}
          placeholder="Ví dụ: AI agent đang thay đổi quy trình mua hàng của doanh nghiệp B2B như thế nào?"
          aria-describedby="question-help"
          disabled={!canStart}
        />
        <div className="question-meta" id="question-help">
          <span>Báo cáo luôn xét năm góc nhìn:</span>
          <ul className="perspective-list">
            {Object.values(PERSPECTIVE_LABELS).map((label) => <li key={label}>{label}</li>)}
          </ul>
          <span className="question-count">{trimmed.length}/1000</span>
        </div>
        {error && <p className="notice error-notice" role="alert">{error}</p>}
        <div className="question-actions">
          <button type="submit" disabled={!canStart || trimmed.length < 10 || submitting} aria-busy={submitting}>
            {submitting ? "Đang bắt đầu…" : "Bắt đầu nghiên cứu"}
          </button>
          <span className="muted">Thường mất 3–6 phút. Có thể rời trang; kết quả nằm trong lịch sử bên dưới.</span>
        </div>
        {canStart && !trimmed && (
          <div className="question-examples">
            <span className="muted">Gợi ý:</span>
            {EXAMPLES.map((example) => (
              <button type="button" className="secondary" key={example} onClick={() => setQuestion(example)}>{example}</button>
            ))}
          </div>
        )}
      </form>

      <section className="run-history" aria-labelledby="run-history-title">
        <h2 id="run-history-title">Lượt nghiên cứu của bạn</h2>
        {history.isLoading && <div className="stack"><div className="skeleton skeleton-block" /><div className="skeleton skeleton-block" /></div>}
        {history.error && <p className="notice error-notice">{history.error.message}</p>}
        {history.data && history.data.items.length === 0 && <p className="muted">Chưa có lượt nào. Câu hỏi đầu tiên của bạn sẽ xuất hiện ở đây.</p>}
        <ul className="run-history-list">
          {history.data?.items.map((run) => (
            <li key={run.id}>
              <Link href={`/research/runs/${run.id}`} className="run-history-item">
                <span className={`run-status ${run.status}`}>{RUN_STATUS_LABELS[run.status]}</span>
                <span className="run-history-question">{run.question}</span>
                <time dateTime={run.created_at}>{dateFormat.format(new Date(run.created_at))}</time>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
