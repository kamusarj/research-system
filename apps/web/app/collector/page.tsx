"use client";

import { FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, vietnameseApiErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";

type Source = { id: string; key: string; name: string; url: string; enabled: boolean; auto_approve_threshold: number };
type QueueItem = { id: string; title: string; source_url: string; score: number; score_breakdown: Record<string, number> };

export default function CollectorPage() {
  const { t } = useI18n();
  const { can } = useAuth();
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function guarded(task: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await task();
    } catch (reason) {
      setMessage("");
      setError(reason instanceof Error ? reason.message : t("unableSave"));
    } finally {
      setBusy(false);
    }
  }
  const sources = useQuery({ queryKey: ["sources"], queryFn: () => api<Source[]>("/collector/sources") });
  const queue = useQuery({ queryKey: ["review-queue"], queryFn: () => api<QueueItem[]>("/collector/review-queue") });

  async function add(event: FormEvent) {
    event.preventDefault();
    const slug = name.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/gi, "d").toLowerCase().replace(/[^a-z0-9]+/g, "-");
    const key = `${slug || "nguon"}-${Date.now().toString().slice(-5)}`;
    await guarded(async () => {
      await api("/collector/sources", { method: "POST", body: JSON.stringify({ key, name, url, type: "rss" }) });
      setName(""); setUrl(""); await sources.refetch();
    });
  }
  async function run(id: string) {
    setMessage(t("runningFeed"));
    await guarded(async () => {
      const result = await api<{ status: string; discovered_count: number; error: string | null }>(`/collector/sources/${id}/run`, { method: "POST" });
      if (result.status === "failed") {
        setMessage("");
        setError(vietnameseApiErrorMessage(result.error));
      } else {
        setMessage(`${t("status." + result.status)}: ${result.discovered_count} ${t("discovered")}`);
      }
      await queue.refetch();
    });
  }
  async function review(id: string, action: "approve" | "reject") {
    await guarded(async () => {
      await api(`/collector/review-queue/${id}/${action}`, { method: "POST" });
      await queue.refetch();
    });
  }

  return (
    <>
      <header className="page-header"><div><p className="eyebrow">{t("intake")}</p><h1>{t("rssCollector")}</h1><p className="page-description">{t("collectorIntro")}</p></div></header>
      <div className="split workspace-split">
        <section className="panel">
          <div className="section-heading compact"><div><h2>{t("addSource")}</h2><p className="muted">{t("collectorSourceHint")}</p></div></div>
          {can("owner") && <form className="form inset-form" onSubmit={add}>
            <label>{t("name")}<input value={name} onChange={(event) => setName(event.target.value)} required /></label>
            <label>{t("feedUrl")}<input type="url" value={url} onChange={(event) => setUrl(event.target.value)} required /></label>
            <button disabled={busy}>{t("addRss")}</button>
          </form>}
          <div className="section-heading"><div><h2>{t("sources")}</h2></div><span>{sources.data?.length ?? 0}</span></div>
          <div className="stack">
            {sources.data?.map((source) => (
              <article className="card compact-card" key={source.id}>
                <div className="list-item-head"><div><span className="badge">RSS</span><h3>{source.name}</h3></div>{can("researcher") && <button disabled={busy} onClick={() => run(source.id)}>{t("runNow")}</button>}</div>
                <p className="muted source-url">{source.url}</p>
              </article>
            ))}
            {sources.isLoading && <div className="table-state"><span className="spinner" />{t("loading")}</div>}
          </div>
          {message && <p className="notice">{message}</p>}
          {error && <p className="notice error-notice" role="alert">{error}</p>}
        </section>
        <section className="panel">
          <div className="section-heading compact"><div><h2>{t("reviewQueue")}</h2><p className="muted">{t("collectorReviewHint")}</p></div><span>{queue.data?.length ?? 0}</span></div>
          <div className="stack">
            {queue.data?.map((item) => (
              <article className="card" key={item.id}>
                <span className="badge">{t("relevance")} {item.score}</span><h3>{item.title}</h3><p className="muted source-url">{item.source_url}</p>
                {can("owner") && <div className="actions"><button disabled={busy} onClick={() => review(item.id, "approve")}>{t("approve")}</button><button className="secondary" disabled={busy} onClick={() => review(item.id, "reject")}>{t("reject")}</button></div>}
              </article>
            ))}
            {queue.isLoading && <div className="table-state"><span className="spinner" />{t("loading")}</div>}
            {!queue.isLoading && queue.data?.length === 0 && <div className="table-state"><strong>{t("noReview")}</strong></div>}
          </div>
        </section>
      </div>
    </>
  );
}
