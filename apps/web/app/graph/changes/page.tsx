"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { GraphChangeSetList } from "@/lib/types";

export default function GraphChangesPage() {
  const { t } = useI18n();
  const changes = useQuery({
    queryKey: ["graph-change-sets"],
    queryFn: () => api<GraphChangeSetList>("/graph/change-sets"),
  });

  return (
    <>
      <header className="page-header">
        <div><p className="eyebrow">{t("governedChanges")}</p><h1>{t("graphChanges")}</h1><p className="page-description">{t("graphChangesIntro")}</p></div>
      </header>
      {changes.error && <p className="notice error-notice">{changes.error.message}</p>}
      <div className="data-table graph-changes-table">
        <div className="table-header"><span>{t("changeSet")}</span><span>{t("origin")}</span><span>{t("mutations")}</span><span>{t("status")}</span><span>{t("updated")}</span></div>
        {changes.data?.items.map((item) => (
          <Link className="table-row" href={`/graph/changes/${item.id}`} key={item.id}>
            <div className="document-cell"><strong>{item.title}</strong><p>{item.summary}</p></div>
            <span>{item.origin_type}</span><strong>{item.mutations.length}</strong><StatusBadge status={item.lifecycle_status} /><time dateTime={item.updated_at}>{new Date(item.updated_at).toLocaleDateString("vi-VN")}</time>
          </Link>
        ))}
        {changes.isLoading && <div className="table-state"><span className="spinner" />{t("loading")}</div>}
        {!changes.isLoading && changes.data?.items.length === 0 && <div className="table-state"><strong>{t("noChangeSets")}</strong></div>}
      </div>
    </>
  );
}
