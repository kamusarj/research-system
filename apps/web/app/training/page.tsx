"use client";

import { FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { API_URL, api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type Example = { id: string; instruction: string; expected_response: string; status: string; pii_status: string; policy_status: string };
type Dataset = { id: string; name: string; version: string; status: string; example_count: number };

export default function TrainingPage() {
  const { t } = useI18n();
  const [instruction, setInstruction] = useState(""); const [expected, setExpected] = useState(""); const [datasetName, setDatasetName] = useState("Business Agent Behaviors");
  const examples = useQuery({ queryKey: ["training-examples"], queryFn: () => api<Example[]>("/training/examples") });
  const datasets = useQuery({ queryKey: ["training-datasets"], queryFn: () => api<Dataset[]>("/training/datasets") });
  async function capture(event: FormEvent) { event.preventDefault(); const raw = await api<{ id: string }>("/training/events", { method: "POST", body: JSON.stringify({ event_type: "expert-demonstration", source: "training-hub-ui", payload: { instruction, expected_response: expected, context: {} }, provenance: { captured_by: "local-user" } }) }); await api(`/training/events/${raw.id}/convert`, { method: "POST" }); setInstruction(""); setExpected(""); examples.refetch(); }
  async function approve(item: Example) { await api(`/training/examples/${item.id}`, { method: "PUT", body: JSON.stringify({ pii_status: "clear", policy_status: "approved" }) }); await api(`/training/examples/${item.id}/accept`, { method: "POST" }); examples.refetch(); }
  async function makeDataset() { await api("/training/datasets", { method: "POST", body: JSON.stringify({ name: datasetName, version: new Date().toISOString().slice(0, 10) }) }); datasets.refetch(); }
  async function build(id: string) { await api(`/training/datasets/${id}/build`, { method: "POST", body: JSON.stringify({}) }); datasets.refetch(); }
  async function exportJsonl(id: string) { const response = await fetch(`${API_URL}/training/datasets/${id}/export`, { method: "POST" }); if (!response.ok) throw new Error(await response.text()); const blob = await response.blob(); const href = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = href; anchor.download = "training-dataset.jsonl"; anchor.click(); URL.revokeObjectURL(href); }
  return <><p className="eyebrow">{t("governedDatasets")}</p><h1>{t("trainingHub")}</h1><div className="split"><section><h2>{t("captureDemo")}</h2><form className="form card" onSubmit={capture}><label>{t("instruction")}<textarea value={instruction} onChange={(e) => setInstruction(e.target.value)} required /></label><label>{t("expectedResponse")}<textarea rows={6} value={expected} onChange={(e) => setExpected(e.target.value)} required /></label><button>{t("createCandidate")}</button></form><h2>{t("reviewQueue")}</h2><div className="stack">{examples.data?.map((item) => <article className="card" key={item.id}><span className="badge">{t(`status.${item.status}`)}</span><h3>{item.instruction}</h3><p className="muted">{item.expected_response}</p>{item.status === "candidate" && <div className="actions"><button onClick={() => approve(item)}>{t("clearAccept")}</button><button className="secondary" onClick={() => api(`/training/examples/${item.id}/reject`, { method: "POST" }).then(() => examples.refetch())}>{t("reject")}</button></div>}</article>)}</div></section><section><h2>{t("datasetVersions")}</h2><div className="actions"><input aria-label={t("name")} value={datasetName} onChange={(e) => setDatasetName(e.target.value)} /><button onClick={makeDataset}>{t("newDataset")}</button></div><div className="stack">{datasets.data?.map((dataset) => <article className="card" key={dataset.id}><span className="badge">{t(`status.${dataset.status}`)}</span><h3>{dataset.name} · {dataset.version}</h3><p className="muted">{dataset.example_count} {t("examples")}</p><div className="actions"><button onClick={() => build(dataset.id)}>{t("buildAccepted")}</button>{dataset.status === "built" && <button className="secondary" onClick={() => exportJsonl(dataset.id)}>{t("exportJsonl")}</button>}</div></article>)}</div></section></div></>;
}
