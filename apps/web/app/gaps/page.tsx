"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type Gap = {
  id: string;
  title: string;
  concept_key: string;
  status: string;
  priority: number;
  coverage_count: number;
  reason: string;
  assigned_to: string | null;
  deep_research_id: string | null;
};

export default function GapsPage() {
  const { t } = useI18n();
  const [assignee, setAssignee] = useState("Research team");
  const [busy, setBusy] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ["knowledge-gaps"],
    queryFn: () => api<Gap[]>("/gaps"),
  });

  async function run(path: string, id: string, body?: object) {
    setBusy(id);
    try {
      await api(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
      await query.refetch();
    } finally {
      setBusy(null);
    }
  }

  return <>
    <p className="eyebrow">{t("graphCoverage")}</p>
    <h1>{t("gapWorkspace")}</h1>
    <p className="muted">{t("gapIntro")}</p>
    <div className="toolbar">
      <button onClick={() => run("/gaps/detect", "detect")}>{busy === "detect" ? t("scanning") : t("scanCoverage")}</button>
      <input aria-label={t("defaultAssignee")} value={assignee} onChange={(event) => setAssignee(event.target.value)} />
      <span className="muted">{query.data?.length ?? 0} {t("trackedGaps")}</span>
    </div>
    {query.error && <p className="error">{query.error.message}</p>}
    <div className="stack">
      {query.data?.map((gap) => {
        const closed = ["dismissed", "filled"].includes(gap.status);
        return <article className="card" key={gap.id}>
          <div className="gap-heading"><div><span className="badge">{t(`status.${gap.status}`)}</span><h2>{gap.title}</h2></div><strong>{t("priority")} {gap.priority}</strong></div>
          <p>{gap.reason}</p>
          <p className="muted">{t("concept")}: {gap.concept_key} · {t("approvedCoverage")}: {gap.coverage_count} · {t("owner")}: {gap.assigned_to ?? t("unassigned")}</p>
          <div className="actions">
            {!gap.assigned_to && !closed && <button disabled={busy === gap.id} onClick={() => run(`/gaps/${gap.id}/assign`, gap.id, { assigned_to: assignee })}>{t("assign")}</button>}
            {!gap.deep_research_id && !closed && <button disabled={busy === gap.id} onClick={() => run(`/gaps/${gap.id}/request-deep-research`, gap.id)}>{t("createDeepDraft")}</button>}
            {gap.deep_research_id && <Link className="button-link" href={`/research/${gap.deep_research_id}`}>{t("openResearch")}</Link>}
            {!closed && <button className="secondary" disabled={busy === gap.id} onClick={() => run(`/gaps/${gap.id}/dismiss`, gap.id, { reason: "Dismissed from workspace" })}>{t("dismiss")}</button>}
          </div>
        </article>;
      })}
      {!query.isLoading && query.data?.length === 0 && <article className="card"><p className="muted">{t("noGaps")}</p></article>}
    </div>
  </>;
}
