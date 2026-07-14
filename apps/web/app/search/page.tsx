"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { ResearchList } from "@/lib/types";

export default function SearchPage() {
  const { t } = useI18n();
  const [input, setInput] = useState("");
  const [type, setType] = useState("");
  const [results, setResults] = useState<ResearchList | null>(null);
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault(); setError("");
    try { setResults(await api<ResearchList>(`/search?q=${encodeURIComponent(input)}${type ? `&type=${type}` : ""}`)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : t("searchFailed")); }
  }
  return <><p className="eyebrow">{t("discovery")}</p><h1>{t("searchResearch")}</h1><form className="searchbar" onSubmit={submit}><input value={input} onChange={(e) => setInput(e.target.value)} placeholder={t("searchApproved")} required /><select value={type} onChange={(e) => setType(e.target.value)}><option value="">{t("allResearchTypes")}</option><option value="internal-research">{t("internalResearch")}</option><option value="reference">{t("reference")}</option><option value="deep-research-report">{t("deepResearch")}</option></select><button>{t("searchAction")}</button></form>{error && <p className="error">{error}</p>}{results && <p className="muted">{results.total} {t("results")}</p>}<div className="stack">{results?.items.map((item) => <Link className="card" href={`/research/${item.id}`} key={item.id}><StatusBadge status={item.status} /><h2>{item.title}</h2><p className="muted">{item.summary}</p></Link>)}</div></>;
}
