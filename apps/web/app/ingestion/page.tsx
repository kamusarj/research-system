"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { StatusBadge } from "@/components/status-badge";

type Provider = { id: string; configured: boolean; active: boolean; model: string };
type Submission = {
  id: string; url: string; source_type: string; status: string; title: string | null;
  content_preview: string; classification: Record<string, unknown>; provider_name: string | null;
  model_name: string | null; error: string | null; research_id: string | null;
};

export default function IngestionPage() {
  const { t } = useI18n();
  const [url, setUrl] = useState("");
  const [provider, setProvider] = useState("mock");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [working, setWorking] = useState(false);
  const providers = useQuery({ queryKey: ["ai-providers"], queryFn: () => api<Provider[]>("/ai/providers") });
  const inbox = useQuery({
    queryKey: ["link-inbox"],
    queryFn: () => api<Submission[]>("/ingestion/links"),
    refetchInterval: (query) => query.state.data?.some((item) =>
      ["queued", "extracting", "retrying"].includes(item.status)
    ) ? 2000 : false,
  });

  async function submit(event: FormEvent) {
    event.preventDefault(); setWorking(true); setError(""); setMessage("");
    try {
      const result = await api<Submission>("/ingestion/links", { method: "POST", body: JSON.stringify({ url, provider, source_type: "manual" }) });
      setMessage(result.status === "queued" ? t("submissionQueued") : `${t("existingSubmission")}: ${t(`status.${result.status}`)}`);
      setUrl(""); await inbox.refetch();
    } catch (reason) { setError(reason instanceof Error ? reason.message : t("submissionFailed")); }
    finally { setWorking(false); }
  }
  async function action(id: string, name: "approve" | "reject" | "retry") {
    await api(`/ingestion/links/${id}/${name}`, { method: "POST", body: name === "approve" ? "{}" : undefined });
    await inbox.refetch();
  }

  return <>
    <header className="page-header"><div><p className="eyebrow">URL → Knowledge</p><h1>{t("intakeTitle")}</h1><p className="muted">{t("intakeIntro")}</p></div><span className="header-chip">API / Discord ready</span></header>
    <section className="intake-panel">
      <form onSubmit={submit} className="intake-form"><label><span>{t("url")}</span><input type="url" placeholder="https://…" value={url} onChange={(event) => setUrl(event.target.value)} required /></label><label><span>{t("provider")}</span><select value={provider} onChange={(event) => setProvider(event.target.value)}>{providers.data?.map((item) => <option key={item.id} value={item.id} disabled={!item.configured}>{item.id} · {item.model} ({item.configured ? t("configured") : t("unavailable")})</option>)}</select></label><button disabled={working}>{working ? t("loading") : t("submit")}</button></form>
      {error && <p className="error">{error}</p>}
      {message && <p className="success">{message}</p>}
    </section>
    <div className="section-heading"><h2>{t("inbox")}</h2><span>{inbox.data?.length ?? 0}</span></div>
    <div className="stack submission-list">{inbox.data?.map((item) => {
      const classification = item.classification as { confidence?: number; relevance_score?: number; summary?: string; technologies?: string[]; business_domains?: string[]; normalized_source?: { source_type?: string; collection_status?: string } };
      return <article className="card submission" key={item.id}><div className="submission-top"><div><StatusBadge status={item.status} /><span className="muted">{item.provider_name ?? "—"} · {classification.normalized_source?.source_type ?? item.source_type}</span></div><a href={item.url} target="_blank" rel="noreferrer">↗</a></div><h3>{item.title ?? item.url}</h3><p>{classification.summary ?? item.content_preview}</p>{item.status === "needs-transcript" && <p className="graph-warning">{t("needsTranscriptHint")}</p>}{item.status === "needs-text-layer" && <p className="graph-warning">{t("needsPdfTextHint")}</p>}{item.error && <p className="error">{item.error}</p>}<div className="submission-meta"><span>{t("confidence")} <strong>{classification.confidence != null ? `${Math.round(classification.confidence * 100)}%` : "—"}</strong></span><span>{t("relevance")} <strong>{classification.relevance_score ?? "—"}</strong></span>{classification.technologies?.map((value) => <span className="tag" key={value}>{value}</span>)}</div><div className="actions">{item.status === "needs-review" && <><button onClick={() => action(item.id, "approve")}>{t("approve")}</button><button className="secondary" onClick={() => action(item.id, "reject")}>{t("reject")}</button></>}{["failed", "dead-letter"].includes(item.status) && <button onClick={() => action(item.id, "retry")}>{t("retry")}</button>}{item.research_id && <Link className="button-link" href={`/research/${item.research_id}`}>{t("openResearch")}</Link>}</div></article>;
    })}{!inbox.isLoading && inbox.data?.length === 0 && <div className="empty-state"><span>↗</span><p>{t("noLinks")}</p></div>}</div>
  </>;
}
