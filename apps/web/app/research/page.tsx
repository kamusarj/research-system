"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Pager } from "@/components/pager";
import { ResearchForm } from "@/components/research-form";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import type { ResearchList } from "@/lib/types";

const tabs = [
  { key: "all", status: "" },
  { key: "review", status: "in-review" },
  { key: "published", status: "approved" },
  { key: "failed", status: "rejected" },
  { key: "archived", status: "archived" },
] as const;
const PAGE_SIZE = 20;

export default function ResearchPage() {
  const { t } = useI18n();
  const { can } = useAuth();
  const [activeTab, setActiveTab] = useState<(typeof tabs)[number]>(tabs[0]);
  const [creating, setCreating] = useState(false);
  const [page, setPage] = useState(1);
  const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (activeTab.status) params.set("status", activeTab.status);
  const query = useQuery({
    queryKey: ["research", activeTab.status, page],
    queryFn: () => api<ResearchList>(`/research?${params.toString()}`),
  });

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">{t("knowledgeBase")}</p>
          <h1>{t("researchLibrary")}</h1>
          <p className="page-description">{t("researchFlowNote")}</p>
        </div>
        {can("researcher") && <button onClick={() => setCreating((value) => !value)}>{creating ? t("closeEditor") : t("newResearch")}</button>}
      </header>
      {creating && can("researcher") && (
        <section className="editor-panel">
          <div className="section-heading compact"><div><h2>{t("newResearch")}</h2><p className="muted">{t("manualResearchHint")}</p></div></div>
          <ResearchForm onSaved={() => { query.refetch(); setCreating(false); }} />
        </section>
      )}
      <div className="research-tabs" role="tablist" aria-label={t("researchLibrary")}>
        {tabs.map((tab) => (
          <button
            key={tab.key}
            role="tab"
            aria-selected={activeTab.key === tab.key}
            className={activeTab.key === tab.key ? "active" : ""}
            onClick={() => { setActiveTab(tab); setPage(1); }}
          >
            {t(`researchTab.${tab.key}`)}
          </button>
        ))}
      </div>
      {query.error && <p className="notice error-notice">{query.error.message}</p>}
      <div className="data-table research-table">
        <div className="table-header"><span>{t("document")}</span><span>{t("type")}</span><span>{t("status")}</span><span>{t("updated")}</span></div>
        {query.data?.items.map((item) => (
          <Link className="table-row" href={`/research/${item.id}`} key={item.id}>
            <div className="document-cell">
              <strong>{item.title}</strong>
              <p>{item.summary || t("noSummary")}</p>
              <div>{item.tags.slice(0, 4).map((tag) => <span className="tag" key={tag}>{tag}</span>)}</div>
            </div>
            <span>{t(item.type === "internal-research" ? "internalResearch" : item.type === "reference" ? "reference" : "deepResearch")}</span>
            <StatusBadge status={item.status} />
            <time dateTime={item.updated_at}>{new Date(item.updated_at).toLocaleDateString("vi-VN")}</time>
          </Link>
        ))}
        {query.isLoading && <div className="table-state"><span className="spinner" />{t("loading")}</div>}
        {!query.isLoading && query.data?.items.length === 0 && <div className="table-state"><strong>{t("noResearchInView")}</strong></div>}
      </div>
      {query.data && <Pager page={page} pageSize={PAGE_SIZE} total={query.data.total} onChange={setPage} />}
    </>
  );
}
