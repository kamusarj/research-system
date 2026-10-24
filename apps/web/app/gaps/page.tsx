"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";

type Gap = { id: string; title: string; concept_key: string; status: string; priority: number; coverage_count: number; reason: string; assigned_to: string | null; deep_research_id: string | null };

export default function GapsPage() {
  const { t } = useI18n();
  const { can, enabled, user } = useAuth();
  const [assignee, setAssignee] = useState(enabled && user ? user.name : "Nhóm nghiên cứu");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const query = useQuery({ queryKey: ["knowledge-gaps"], queryFn: () => api<Gap[]>("/gaps") });
  const router = useRouter();
  const features = useQuery({
    queryKey: ["system-features"],
    queryFn: () => api<{ research_agent?: boolean }>("/system/features"),
    staleTime: 60_000,
  });
  const researchAgent = features.data?.research_agent === true;

  // Khi pipeline nghiên cứu sâu bật: chạy tìm nguồn + kiểm chứng thật và mở màn theo dõi tiến độ.
  async function startResearch(gap: Gap) {
    setBusy(gap.id);
    setError("");
    try {
      const run = await api<{ id: string }>(`/gaps/${gap.id}/research-run`, { method: "POST" });
      router.push(`/research/runs/${run.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("unableSave"));
      setBusy(null);
    }
  }

  async function run(path: string, id: string, body?: object) {
    setBusy(id);
    setError("");
    try {
      await api(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
      await query.refetch();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("unableSave"));
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <header className="page-header">
        <div><p className="eyebrow">{t("graphCoverage")}</p><h1>{t("gapWorkspace")}</h1><p className="page-description">{t("gapIntro")}</p></div>
        <span className="badge">{query.data?.length ?? 0} {t("trackedGaps")}</span>
      </header>
      {can("researcher") && <div className="toolbar">
        <button onClick={() => run("/gaps/detect", "detect")}>{busy === "detect" ? t("scanning") : t("scanCoverage")}</button>
        <input aria-label={t("defaultAssignee")} value={assignee} onChange={(event) => setAssignee(event.target.value)} />
      </div>}
      {query.error && <p className="notice error-notice">{query.error.message}</p>}
      {error && <p className="notice error-notice" role="alert">{error}</p>}
      <div className="stack gap-list">
        {query.data?.map((gap) => {
          const closed = ["dismissed", "filled"].includes(gap.status);
          return (
            <article className="card" key={gap.id}>
              <div className="gap-heading"><div><StatusBadge status={gap.status} /><h2>{gap.title}</h2></div><strong>{t("priority")} {gap.priority}</strong></div>
              <p>{gap.reason}</p>
              <p className="muted">{t("concept")}: {gap.concept_key} · {t("approvedCoverage")}: {gap.coverage_count} · {t("owner")}: {gap.assigned_to ?? t("unassigned")}</p>
              <div className="actions">
                {can("researcher") && !gap.assigned_to && !closed && <button disabled={busy === gap.id} onClick={() => run(`/gaps/${gap.id}/assign`, gap.id, { assigned_to: assignee })}>{t("assign")}</button>}
                {can("researcher") && !gap.deep_research_id && !closed && (researchAgent
                  ? <button disabled={busy === gap.id} onClick={() => void startResearch(gap)}>Nghiên cứu sâu có trích dẫn</button>
                  : <button disabled={busy === gap.id} onClick={() => run(`/gaps/${gap.id}/request-deep-research`, gap.id)}>{t("createDeepDraft")}</button>)}
                {gap.deep_research_id && <Link className="button-link" href={`/research/${gap.deep_research_id}`}>{t("openResearch")}</Link>}
                {can("researcher") && !closed && <button className="secondary" disabled={busy === gap.id} onClick={() => run(`/gaps/${gap.id}/dismiss`, gap.id, { reason: "Đã bỏ qua trong không gian nghiên cứu" })}>{t("dismiss")}</button>}
              </div>
            </article>
          );
        })}
        {query.isLoading && <div className="card table-state"><span className="spinner" />{t("loading")}</div>}
        {!query.isLoading && query.data?.length === 0 && <article className="card table-state"><strong>{t("noGaps")}</strong></article>}
      </div>
    </>
  );
}
