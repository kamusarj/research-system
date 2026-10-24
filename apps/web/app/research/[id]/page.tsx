"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { ResearchForm } from "@/components/research-form";
import { AIPanel } from "@/components/ai-panel";
import { StatusBadge } from "@/components/status-badge";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import type { Research } from "@/lib/types";
import { ReportMarkdown } from "@/components/report-markdown";

export default function ResearchDetail() {
  const { t } = useI18n();
  const { can } = useAuth();
  const { id } = useParams<{ id: string }>();
  const query = useQuery({ queryKey: ["research", id], queryFn: () => api<Research>(`/research/${id}`) });
  const [pending, setPending] = useState<string | null>(null);
  const [actionError, setActionError] = useState("");

  async function action(name: "submit-review" | "approve" | "reject" | "archive") {
    setPending(name);
    setActionError("");
    try {
      await api(`/research/${id}/${name}`, { method: "POST" });
      await query.refetch();
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : t("unableSave"));
    } finally {
      setPending(null);
    }
  }

  if (query.isLoading) return <div className="table-state page-loading"><span className="spinner" />{t("loading")}</div>;
  if (query.error && !(query.error instanceof ApiError && query.error.status === 404)) {
    return <div className="card table-state"><strong className="error">{query.error.message}</strong><button onClick={() => void query.refetch()}>{t("retry")}</button></div>;
  }
  if (!query.data) return <div className="card table-state"><strong className="error">{t("notFound")}</strong><Link className="button-link" href="/research">{t("viewLibrary")}</Link></div>;
  const item = query.data;
  // Nội dung đang duyệt/đã xuất bản chỉ chủ sở hữu được sửa (máy chủ cũng kiểm tra).
  const canEdit = can("owner") || (can("researcher") && !["in-review", "approved"].includes(item.status));
  const busy = pending !== null;

  return (
    <>
      <Link className="back-link" href="/research">← {t("viewLibrary")}</Link>
      <header className="page-header research-detail-header">
        <div>
          <p className="eyebrow">{item.display_id}</p><h1>{item.title}</h1>
          <div className="detail-meta"><StatusBadge status={item.status} />{item.tags.map((tag) => <span className="tag" key={tag}>{tag}</span>)}</div>
        </div>
        <div className="actions detail-actions">
          {can("researcher") && ["draft", "rejected"].includes(item.status) && <button disabled={busy} onClick={() => action("submit-review")}>{t("submitReview")}</button>}
          {can("owner") && item.status === "in-review" && <><button disabled={busy} onClick={() => action("approve")}>{t("approve")}</button><button className="secondary" disabled={busy} onClick={() => action("reject")}>{t("reject")}</button></>}
          {can("owner") && item.status !== "archived" && <button className="secondary" disabled={busy} onClick={() => action("archive")}>{t("archive")}</button>}
        </div>
      </header>
      {actionError && <p className="notice error-notice" role="alert">{actionError}</p>}
      <div className="split detail-layout">
        <section className="stack">
          <article className="card prose research-content">
            <div className="section-heading compact"><div><p className="eyebrow">{t("content")}</p><h2>{t("summary")}</h2></div></div>
            {item.summary && <p className="research-summary">{item.summary}</p>}
            <ReportMarkdown content={item.content} />
            {item.source_url && <a className="source-link original-source" href={item.source_url} target="_blank" rel="noreferrer">{t("openOriginalSource")} ↗</a>}
          </article>
          {can("researcher") && <AIPanel researchId={item.id} onAccepted={() => query.refetch()} />}
        </section>
        {canEdit && <section className="panel edit-panel">
          <div className="section-heading compact"><div><p className="eyebrow">{t("edit")}</p><h2>{t("saveVersion")}</h2></div></div>
          {/* key: dựng lại form khi bản ghi đổi (ví dụ vừa chấp nhận gợi ý AI) để không lưu đè giá trị cũ. */}
          <ResearchForm key={item.updated_at} item={item} onSaved={() => query.refetch()} />
        </section>}
        {!canEdit && can("researcher") && <section className="panel edit-panel">
          <p className="muted">Nghiên cứu đang chờ duyệt hoặc đã xuất bản chỉ chủ sở hữu được chỉnh sửa. Hãy để lại góp ý cho chủ sở hữu.</p>
        </section>}
      </div>
    </>
  );
}
