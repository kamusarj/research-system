"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { GraphChangeReview } from "@/components/graph-change-review";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { changeSetAction } from "@/lib/graph-changes";
import { useI18n } from "@/lib/i18n";
import type { GraphChangeSet } from "@/lib/types";

export default function GraphChangeSetDetail() {
  const { t } = useI18n();
  const { can } = useAuth();
  const { id } = useParams<{ id: string }>();
  const [acting, setActing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ["graph-change-set", id],
    queryFn: () => api<GraphChangeSet>(`/graph/change-sets/${id}`),
  });

  async function action(name: "validate" | "approve" | "reject" | "apply" | "compensate") {
    setActing(true);
    setError(null);
    try {
      const result = await changeSetAction(id, name);
      if (name === "compensate") {
        window.location.assign(`/graph/changes/${result.id}`);
        return;
      }
      await query.refetch();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("actionFailed"));
    } finally {
      setActing(false);
    }
  }

  if (query.isLoading) return <div className="table-state page-loading"><span className="spinner" />{t("loading")}</div>;
  if (!query.data) return <div className="card table-state"><strong>{t("changeSetNotFound")}</strong><Link className="button-link" href="/graph/changes">{t("graphChanges")}</Link></div>;
  const item = query.data;
  const editable = ["draft", "needs_review"].includes(item.lifecycle_status);
  const summary = item.validation_summary;

  return (
    <>
      <Link className="back-link" href="/graph/changes">← {t("graphChanges")}</Link>
      <header className="page-header">
        <div><p className="eyebrow">{item.origin_type} · {item.id.slice(0, 8)}</p><h1>{item.title}</h1><p className="page-description">{item.summary}</p><div className="detail-meta"><StatusBadge status={item.lifecycle_status} /><span className="tag">{item.mutations.length} {t("mutations")}</span></div></div>
        <div className="actions detail-actions">
          {can("researcher") && <Link className="button-link secondary" href={`/chat?scope_type=change_set&scope_id=${item.id}`}>{t("brainstormChanges")}</Link>}
          {can("researcher") && editable && <button className="secondary" disabled={acting} onClick={() => action("validate")}>{t("validateChanges")}</button>}
          {can("owner") && editable && <button disabled={acting} onClick={() => action("approve")}>{t("approveAll")}</button>}
          {can("owner") && editable && <button className="secondary" disabled={acting} onClick={() => action("reject")}>{t("rejectAll")}</button>}
          {can("owner") && item.lifecycle_status === "approved" && <button disabled={acting} onClick={() => action("apply")}>{t("applyChanges")}</button>}
          {can("owner") && item.lifecycle_status === "applied" && <button className="secondary" disabled={acting} onClick={() => action("compensate")}>{t("createUndo")}</button>}
        </div>
      </header>
      {error && <p className="notice error-notice">{error}</p>}
      <section className="change-validation-strip">
        <div><span>{t("validMutations")}</span><strong>{summary.valid_count ?? 0}</strong></div>
        <div><span>{t("warnings")}</span><strong>{summary.warning_count ?? 0}</strong></div>
        <div><span>{t("errors")}</span><strong>{summary.error_count ?? 0}</strong></div>
        <div><span>{t("appliedAt")}</span><strong>{item.applied_at ? new Date(item.applied_at).toLocaleString("vi-VN") : "—"}</strong></div>
      </section>
      <section className="change-review-list">
        {item.mutations.map((mutation) => <GraphChangeReview key={mutation.id} changeSetId={item.id} mutation={mutation} editable={editable && can("owner")} onChanged={() => query.refetch()} />)}
      </section>
    </>
  );
}
