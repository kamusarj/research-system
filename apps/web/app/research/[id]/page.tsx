"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { ResearchForm } from "@/components/research-form";
import { AIPanel } from "@/components/ai-panel";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Research } from "@/lib/types";

export default function ResearchDetail() {
  const { t } = useI18n();
  const { id } = useParams<{ id: string }>();
  const query = useQuery({ queryKey: ["research", id], queryFn: () => api<Research>(`/research/${id}`) });
  async function action(name: "submit-review" | "approve" | "reject" | "archive") { await api(`/research/${id}/${name}`, { method: "POST" }); query.refetch(); }
  if (query.isLoading) return <p>{t("loading")}</p>;
  if (!query.data) return <p className="error">{t("notFound")}</p>;
  const item = query.data;
  return <><p className="eyebrow">{item.display_id}</p><h1>{item.title}</h1><p><StatusBadge status={item.status} /> {item.tags.map((tag) => <span className="tag" key={tag}>{tag}</span>)}</p><div className="actions">{["draft", "rejected"].includes(item.status) && <button onClick={() => action("submit-review")}>{t("submitReview")}</button>}{item.status === "in-review" && <><button onClick={() => action("approve")}>{t("approve")}</button><button className="secondary" onClick={() => action("reject")}>{t("reject")}</button></>}{item.status !== "archived" && <button className="secondary" onClick={() => action("archive")}>{t("archive")}</button>}</div><div className="split"><section><h2>{t("content")}</h2><article className="card prose"><p>{item.summary}</p><pre>{item.content}</pre>{item.source_url && <a className="source-link" href={item.source_url} target="_blank" rel="noreferrer">{t("openOriginalSource")} ↗</a>}</article><AIPanel researchId={item.id} onAccepted={() => query.refetch()} /></section><section><h2>{t("edit")}</h2><ResearchForm item={item} onSaved={() => query.refetch()} /></section></div></>;
}
