"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import type { ResearchList, SourceSubmission } from "@/lib/types";

export default function Dashboard() {
  const { t } = useI18n();
  const { can } = useAuth();
  const research = useQuery({ queryKey: ["dashboard-research"], queryFn: () => api<ResearchList>("/research?page_size=6") });
  const sources = useQuery({ queryKey: ["dashboard-sources"], queryFn: () => api<SourceSubmission[]>("/ingestion/links") });
  const documents = research.data?.items ?? [];
  const submissions = sources.data ?? [];
  const active = submissions.filter((item) => ["pending", "processing", "fetching", "extracting", "analyzing"].includes(item.status)).length;
  const review = submissions.filter((item) => item.review_status === "needs_review").length;
  const failed = submissions.filter((item) => item.status === "failed").length;

  return (
    <div className="dashboard">
      <section className="dash-hero">
        <div className="dash-hero-content">
          <span className="dash-hero-eyebrow"><span aria-hidden="true">✦</span>{t("dashboardHeroKicker")}</span>
          <h1>{t("dashboardHeroLead")} <span>{t("dashboardHeroAccent")}</span></h1>
          <p>{t("dashboardIntro")}</p>
          <div className="dash-hero-actions">
            {can("researcher") && <Link className="primary-link" href="/ingestion"><span aria-hidden="true">+</span>{t("addSources")}</Link>}
            <Link className="secondary-link" href="/research">{t("viewLibrary")}</Link>
          </div>
          <div className="dash-hero-proof" aria-label={t("pipelineOverview")}>
            <span>{t("safeExtraction")}</span>
            <span>{t("humanReview")}</span>
            <span>{t("connectedGraph")}</span>
          </div>
        </div>
        <div className="dash-hero-preview" aria-hidden="true">
          <div className="hero-preview-label">{t("pipelineLive")}</div>
          <strong>{t("sourceToKnowledge")}</strong>
          <div className="dash-hero-preview-row"><span>{t("processing")}</span><b>{active}</b></div>
          <div className="dash-hero-preview-row"><span>{t("needsReview")}</span><b>{review}</b></div>
          <div className="dash-hero-preview-row"><span>{t("failed")}</span><em>{failed}</em></div>
          <i className="preview-track"><span /></i>
        </div>
      </section>

      <section aria-labelledby="quick-start-title">
        <div className="dash-section-head">
          <div><span className="section-kicker">{t("suggestedWorkflow")}</span><h2 id="quick-start-title">{t("quickStart")}</h2></div>
        </div>
        <div className="quick-start-grid">
          <Link href="/ingestion" className="quick-start-card quick-start-primary">
            <span className="quick-start-step">01</span><span className="quick-start-icon" aria-hidden="true">＋</span>
            <strong>{t("addSources")}</strong><p>{t("quickSourceDescription")}</p><span className="quick-start-link">{t("openIntake")} →</span>
          </Link>
          <Link href="/research" className="quick-start-card">
            <span className="quick-start-step">02</span><span className="quick-start-icon" aria-hidden="true">▤</span>
            <strong>{t("researchLibrary")}</strong><p>{t("quickReviewDescription")}</p><span className="quick-start-link">{t("viewLibrary")} →</span>
          </Link>
          <Link href="/graph" className="quick-start-card">
            <span className="quick-start-step">03</span><span className="quick-start-icon" aria-hidden="true">⌘</span>
            <strong>{t("graphTitle")}</strong><p>{t("quickGraphDescription")}</p><span className="quick-start-link">{t("exploreGraph")} →</span>
          </Link>
        </div>
      </section>

      <section aria-label={t("pipelineOverview")}>
        <div className="dash-section-head"><div><span className="section-kicker">{t("workspaceHealth")}</span><h2>{t("pipelineOverview")}</h2></div></div>
        <div className="metric-grid">
          <Link href="/research"><span className="metric-icon" aria-hidden="true">▤</span><span>{t("documents")}</span><strong>{research.data?.total ?? 0}</strong><small>{t("inLibrary")}</small></Link>
          <Link href="/ingestion"><span className="metric-icon" aria-hidden="true">↻</span><span>{t("processing")}</span><strong>{active}</strong><small>{t("activeJobs")}</small></Link>
          <Link href="/ingestion"><span className="metric-icon" aria-hidden="true">✓</span><span>{t("needsReview")}</span><strong>{review}</strong><small>{t("awaitingDecision")}</small></Link>
          <Link href="/ingestion"><span className="metric-icon" aria-hidden="true">!</span><span>{t("failed")}</span><strong>{failed}</strong><small>{t("canRetry")}</small></Link>
        </div>
      </section>

      <div className="dashboard-grid">
        <section>
          <div className="section-heading">
            <div><h2>{t("recentDocuments")}</h2><p className="muted">{t("recentDocumentsHint")}</p></div>
            <Link className="text-link" href="/research">{t("viewLibrary")} →</Link>
          </div>
          <div className="data-table document-table">
            <div className="table-header"><span>{t("document")}</span><span>{t("status")}</span><span>{t("updated")}</span></div>
            {documents.map((item) => (
              <Link className="table-row" href={`/research/${item.id}`} key={item.id}>
                <div className="document-cell"><strong>{item.title}</strong><p>{item.summary || t("noSummary")}</p></div>
                <StatusBadge status={item.status} />
                <time dateTime={item.updated_at}>{new Date(item.updated_at).toLocaleDateString("vi-VN")}</time>
              </Link>
            ))}
            {(research.isLoading || sources.isLoading) && <div className="table-state"><span className="spinner" />{t("loading")}</div>}
            {!research.isLoading && documents.length === 0 && <div className="table-state"><strong>{t("noResearchInView")}</strong><span>{t("noLinksHint")}</span></div>}
          </div>
        </section>
        <aside className="activity-panel">
          <div className="section-heading"><div><h2>{t("sourceActivity")}</h2><p className="muted">{t("latestPipelineEvents")}</p></div></div>
          <div className="activity-list">
            {submissions.slice(0, 6).map((item) => (
              <Link href="/ingestion" key={item.id}>
                <StatusBadge status={item.status} /><strong>{item.title || item.url}</strong>
                <time dateTime={item.updated_at}>{new Date(item.updated_at).toLocaleString("vi-VN")}</time>
              </Link>
            ))}
            {!sources.isLoading && submissions.length === 0 && <p className="muted">{t("noLinks")}</p>}
          </div>
        </aside>
      </div>
    </div>
  );
}
