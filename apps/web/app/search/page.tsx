"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { Pager } from "@/components/pager";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { ResearchList } from "@/lib/types";

export default function SearchPage() {
  const { t } = useI18n();
  const [input, setInput] = useState("");
  const [type, setType] = useState("");
  const [results, setResults] = useState<ResearchList | null>(null);
  const [submitted, setSubmitted] = useState<{ q: string; type: string } | null>(null);
  const [error, setError] = useState("");

  async function load(search: { q: string; type: string }, page: number) {
    setError("");
    const params = new URLSearchParams({ q: search.q, page: String(page), page_size: "20" });
    if (search.type) params.set("type", search.type);
    try {
      setResults(await api<ResearchList>(`/search?${params.toString()}`));
      setSubmitted(search);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("searchFailed"));
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    await load({ q: input, type }, 1);
  }

  return (
    <>
      <header className="page-header">
        <div><p className="eyebrow">{t("discovery")}</p><h1>{t("searchResearch")}</h1><p className="page-description">{t("searchPageIntro")}</p></div>
      </header>
      <form className="searchbar" onSubmit={submit}>
        <input value={input} onChange={(event) => setInput(event.target.value)} placeholder={t("searchApproved")} required />
        <select value={type} onChange={(event) => setType(event.target.value)}>
          <option value="">{t("allResearchTypes")}</option>
          <option value="internal-research">{t("internalResearch")}</option>
          <option value="reference">{t("reference")}</option>
          <option value="deep-research-report">{t("deepResearch")}</option>
        </select>
        <button>{t("searchAction")}</button>
      </form>
      {error && <p className="notice error-notice">{error}</p>}
      {results && (
        <section className="search-results">
          <div className="section-heading"><div><span className="section-kicker">{t("discovery")}</span><h2>{results.total} {t("results")}</h2></div></div>
          <div className="stack">
            {results.items.map((item) => (
              <Link className="card list-card" href={`/research/${item.id}`} key={item.id}>
                <StatusBadge status={item.status} /><h3>{item.title}</h3><p className="muted">{item.summary || t("noSummary")}</p>
              </Link>
            ))}
            {results.items.length === 0 && <div className="card table-state"><strong>{t("noSearchResults")}</strong><span>{t("adjustSearch")}</span></div>}
          </div>
          {submitted && <Pager page={results.page} pageSize={results.page_size} total={results.total} onChange={(page) => void load(submitted, page)} />}
        </section>
      )}
    </>
  );
}
