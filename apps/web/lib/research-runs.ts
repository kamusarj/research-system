import { API_URL } from "@/lib/api";

export type Perspective = "market" | "use_case" | "competitors" | "technical" | "risk_compliance";
export type RunStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export type ResearchRunEvent = {
  id: number;
  kind: "stage" | "progress" | "warning" | "error" | "done";
  stage: string;
  message: string;
  data: Record<string, unknown>;
  created_at: string;
};

export type ResearchRunSource = {
  id: string;
  provider: string;
  perspective: Perspective;
  url: string;
  domain: string;
  title: string;
  status: string;
  suspicious: boolean;
  citation_index: number | null;
  error_code: string | null;
};

export type ResearchRunClaim = {
  id: string;
  source_id: string;
  perspective: Perspective;
  text: string;
  quote: string;
  matched_quote: string | null;
  match_method: string;
  entailment: string;
  status: string;
  reason: string | null;
  used_in_report: boolean;
};

export type ResearchRun = {
  id: string;
  question: string;
  status: RunStatus;
  stage: string;
  variant: string;
  provider_name: string | null;
  model_name: string | null;
  knowledge_gap_id: string | null;
  report_research_id: string | null;
  error_code: string | null;
  error_message: string | null;
  metrics: Record<string, unknown>;
  created_by: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type ResearchRunDetail = ResearchRun & {
  report_markdown: string | null;
  sources: ResearchRunSource[];
  claims: ResearchRunClaim[];
  events: ResearchRunEvent[];
};

export const PERSPECTIVE_LABELS: Record<Perspective, string> = {
  market: "Thị trường",
  use_case: "Use case",
  competitors: "Đối thủ",
  technical: "Kỹ thuật",
  risk_compliance: "Rủi ro & tuân thủ",
};

export const RUN_STATUS_LABELS: Record<RunStatus, string> = {
  queued: "Đang chờ",
  running: "Đang chạy",
  completed: "Hoàn tất",
  failed: "Thất bại",
  cancelled: "Đã hủy",
};

export const TERMINAL_STATUSES: RunStatus[] = ["completed", "failed", "cancelled"];

export function isTerminal(status: RunStatus): boolean {
  return TERMINAL_STATUSES.includes(status);
}

export type StageStep = {
  key: string;
  label: string;
  detail: (metrics: Record<string, unknown>) => string | null;
};

const count = (metrics: Record<string, unknown>, key: string) =>
  typeof metrics[key] === "number" ? (metrics[key] as number) : null;

export const STAGE_STEPS: StageStep[] = [
  { key: "planning", label: "Lập kế hoạch", detail: (m) => (count(m, "queries_planned") !== null ? `${count(m, "queries_planned")} truy vấn` : null) },
  { key: "searching", label: "Tìm kiếm", detail: (m) => (count(m, "sources_discovered") !== null ? `${count(m, "sources_discovered")} nguồn ứng viên` : null) },
  { key: "fetching", label: "Đọc nguồn", detail: (m) => (count(m, "sources_ready") !== null ? `${count(m, "sources_ready")} nguồn đọc được` : null) },
  { key: "extracting", label: "Trích nhận định", detail: (m) => (count(m, "claims_proposed") !== null ? `${count(m, "claims_proposed")} nhận định` : null) },
  { key: "verifying", label: "Kiểm chứng", detail: (m) => (count(m, "claims_verified") !== null ? `${count(m, "claims_verified")} đã kiểm chứng` : null) },
  { key: "writing", label: "Viết báo cáo", detail: (m) => (count(m, "sources_cited") !== null ? `${count(m, "sources_cited")} nguồn trích dẫn` : null) },
];

export type StepState = "done" | "current" | "pending" | "failed";

export function stepStates(run: Pick<ResearchRun, "stage" | "status">): StepState[] {
  const index = STAGE_STEPS.findIndex((step) => step.key === run.stage);
  return STAGE_STEPS.map((_, position) => {
    if (run.status === "completed" || run.stage === "done") return "done";
    if (index === -1) return "pending";
    if (position < index) return "done";
    if (position === index) return run.status === "failed" ? "failed" : run.status === "cancelled" ? "pending" : "current";
    return "pending";
  });
}

/** Ánh xạ số trích dẫn [n] → nguồn và các trích dẫn nguyên văn đã dùng trong báo cáo. */
export function citationIndex(detail: Pick<ResearchRunDetail, "sources" | "claims">) {
  const map = new Map<number, { source: ResearchRunSource; claims: ResearchRunClaim[] }>();
  for (const source of detail.sources) {
    if (source.citation_index === null) continue;
    map.set(source.citation_index, {
      source,
      claims: detail.claims.filter((claim) => claim.source_id === source.id && claim.used_in_report),
    });
  }
  return map;
}

export type RunStreamHandlers = {
  onEvent: (event: ResearchRunEvent) => void;
  onEnd: () => void;
  onUnavailable: () => void;
};

/**
 * Nhận sự kiện tiến độ qua Server-Sent Events. Trình duyệt tự nối lại (gửi Last-Event-ID) khi
 * máy chủ đóng luồng định kỳ; nếu luồng không mở được (proxy đệm, trình duyệt cũ) thì báo để
 * trang chuyển sang hỏi định kỳ.
 */
export function subscribeRunEvents(runId: string, after: number, handlers: RunStreamHandlers): () => void {
  if (typeof window === "undefined" || typeof window.EventSource === "undefined") {
    handlers.onUnavailable();
    return () => {};
  }
  const source = new EventSource(`${API_URL}/research-runs/${encodeURIComponent(runId)}/events/stream?after=${after}`, { withCredentials: true });
  let opened = false;
  const listener = (message: MessageEvent<string>) => {
    try {
      handlers.onEvent(JSON.parse(message.data) as ResearchRunEvent);
    } catch {
      // Bỏ qua khung dữ liệu hỏng; lần tải lại chi tiết sẽ đồng bộ đầy đủ.
    }
  };
  for (const kind of ["stage", "progress", "warning", "error", "done"]) source.addEventListener(kind, listener as EventListener);
  source.addEventListener("open", () => { opened = true; });
  source.addEventListener("end", () => {
    source.close();
    handlers.onEnd();
  });
  source.addEventListener("error", () => {
    if (!opened) {
      source.close();
      handlers.onUnavailable();
    }
  });
  return () => source.close();
}
