"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ResearchForm } from "@/components/research-form";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { ResearchList } from "@/lib/types";

const tabs = [
  { key: "all", status: "" },
  { key: "review", status: "in-review" },
  { key: "published", status: "approved" },
  { key: "failed", status: "rejected" },
] as const;

export default function ResearchPage() {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<(typeof tabs)[number]>(tabs[0]);
  const path = `/research${activeTab.status ? `?status=${activeTab.status}` : ""}`;
  const query = useQuery({
    queryKey: ["research", activeTab.status],
    queryFn: () => api<ResearchList>(path),
  });
  return (
    <>
      <p className="eyebrow">{t("knowledgeBase")}</p>
      <h1>{t("researchLibrary")}</h1>
      <p className="muted research-flow-note">{t("researchFlowNote")}</p>
      <div className="research-tabs" role="tablist" aria-label={t("researchLibrary")}>
        {tabs.map((tab) => (
          <button
            key={tab.key}
            role="tab"
            aria-selected={activeTab.key === tab.key}
            className={activeTab.key === tab.key ? "active" : ""}
            onClick={() => setActiveTab(tab)}
          >
            {t(`researchTab.${tab.key}`)}
          </button>
        ))}
      </div>
      <div className="split research-layout">
        <section>
          <h2>{t("newResearch")}</h2>
          <ResearchForm onSaved={() => query.refetch()} />
        </section>
        <section>
          <div className="section-heading"><h2>{t("library")}</h2><span>{query.data?.total ?? 0}</span></div>
          {query.isLoading && <p className="muted">{t("loading")}</p>}
          {query.error && <p className="error">{query.error.message}</p>}
          <div className="stack">
            {query.data?.items.map((item) => (
              <Link className="card list-card" href={`/research/${item.id}`} key={item.id}>
                <div><StatusBadge status={item.status} /> <span className="muted">{item.display_id}</span></div>
                <h3>{item.title}</h3>
                <p className="muted">{item.summary || t("noSummary")}</p>
                <div>{item.tags.map((tag) => <span className="tag" key={tag}>{tag}</span>)}</div>
              </Link>
            ))}
            {!query.isLoading && query.data?.items.length === 0 && (
              <div className="empty-state"><span>▤</span><p>{t("noResearchInView")}</p></div>
            )}
          </div>
        </section>
      </div>
    </>
  );
}
