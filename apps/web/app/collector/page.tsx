"use client";

import { FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type Source = { id: string; key: string; name: string; url: string; enabled: boolean; auto_approve_threshold: number };
type QueueItem = { id: string; title: string; source_url: string; score: number; score_breakdown: Record<string, number> };

export default function CollectorPage() {
  const { t } = useI18n();
  const [name, setName] = useState(""); const [url, setUrl] = useState(""); const [message, setMessage] = useState("");
  const sources = useQuery({ queryKey: ["sources"], queryFn: () => api<Source[]>("/collector/sources") });
  const queue = useQuery({ queryKey: ["review-queue"], queryFn: () => api<QueueItem[]>("/collector/review-queue") });
  async function add(event: FormEvent) { event.preventDefault(); const key = `${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${Date.now().toString().slice(-5)}`; await api("/collector/sources", { method: "POST", body: JSON.stringify({ key, name, url, type: "rss" }) }); setName(""); setUrl(""); sources.refetch(); }
  async function run(id: string) { setMessage(t("runningFeed")); const result = await api<{ status: string; discovered_count: number }>(`/collector/sources/${id}/run`, { method: "POST" }); setMessage(`${result.status}: ${result.discovered_count} ${t("discovered")}`); queue.refetch(); }
  async function review(id: string, action: "approve" | "reject") { await api(`/collector/review-queue/${id}/${action}`, { method: "POST" }); queue.refetch(); }
  return <><p className="eyebrow">{t("intake")}</p><h1>{t("rssCollector")}</h1><div className="split"><section><h2>{t("addSource")}</h2><form className="form card" onSubmit={add}><label>{t("name")}<input value={name} onChange={(e) => setName(e.target.value)} required /></label><label>{t("feedUrl")}<input type="url" value={url} onChange={(e) => setUrl(e.target.value)} required /></label><button>{t("addRss")}</button></form><h2>{t("sources")}</h2><div className="stack">{sources.data?.map((source) => <article className="card" key={source.id}><h3>{source.name}</h3><p className="muted">{source.url}</p><button onClick={() => run(source.id)}>{t("runNow")}</button></article>)}</div>{message && <p>{message}</p>}</section><section><h2>{t("reviewQueue")}</h2><div className="stack">{queue.data?.map((item) => <article className="card" key={item.id}><span className="badge">score {item.score}</span><h3>{item.title}</h3><div className="actions"><button onClick={() => review(item.id, "approve")}>{t("approve")}</button><button className="secondary" onClick={() => review(item.id, "reject")}>{t("reject")}</button></div></article>)}{queue.data?.length === 0 && <p className="muted">{t("noReview")}</p>}</div></section></div></>;
}
