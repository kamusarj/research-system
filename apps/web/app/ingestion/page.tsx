"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { IntakeForm } from "@/components/intake/intake-form";
import { ProviderStatus } from "@/components/intake/provider-status";
import { ReviewBacklog } from "@/components/intake/review-backlog";
import { SubmissionList } from "@/components/intake/submission-list";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { PartialIntakeError, isActiveSubmission } from "@/lib/intake";
import { useI18n } from "@/lib/i18n";
import type { Provider, ReviewBacklog as ReviewBacklogSummary, SourceSubmission } from "@/lib/types";

export default function IngestionPage() {
  const { t } = useI18n();
  const { can } = useAuth();
  // A preflight costs one network call per provider, so it is only run when asked for.
  const [preflight, setPreflight] = useState(false);
  const providers = useQuery({
    queryKey: ["ai-providers", preflight],
    queryFn: () => api<Provider[]>(`/ai/providers${preflight ? "?preflight=true" : ""}`),
  });
  const inbox = useQuery({
    queryKey: ["link-inbox"],
    queryFn: () => api<SourceSubmission[]>("/ingestion/links"),
    refetchInterval: (query) => query.state.data?.some((item) => isActiveSubmission(item.status)) ? 1500 : false,
  });
  const backlog = useQuery({
    queryKey: ["link-backlog"],
    queryFn: () => api<ReviewBacklogSummary>("/ingestion/links/backlog"),
  });

  async function refresh() {
    await Promise.all([inbox.refetch(), backlog.refetch()]);
  }

  async function bulkReview(decision: "approve" | "reject") {
    await api("/ingestion/links/bulk-review", {
      method: "POST",
      body: JSON.stringify({ decision }),
    });
    await refresh();
  }

  async function submit(urls: string[], provider: string) {
    const settled = await Promise.allSettled(
      urls.map((url) => api<SourceSubmission>("/ingestion/links", {
        method: "POST",
        body: JSON.stringify({ url, provider, source_type: "manual" }),
      })),
    );
    await refresh();
    const results = settled
      .filter((item): item is PromiseFulfilledResult<SourceSubmission> => item.status === "fulfilled")
      .map((item) => item.value);
    const failedUrls = urls.filter((_url, index) => settled[index].status === "rejected");
    if (failedUrls.length) {
      const firstFailure = settled.find((item) => item.status === "rejected") as PromiseRejectedResult;
      const reason = firstFailure.reason instanceof Error ? ` ${firstFailure.reason.message}` : "";
      throw new PartialIntakeError(
        t("someSourcesRejected").replace("{count}", String(failedUrls.length)) + reason,
        failedUrls,
      );
    }
    return results;
  }

  async function action(id: string, name: "approve" | "reject" | "retry") {
    await api(`/ingestion/links/${id}/${name}`, {
      method: "POST",
      body: name === "approve" ? "{}" : undefined,
    });
    await refresh();
  }

  async function saveTranscript(id: string, language: string, segments: Array<{ timestamp_seconds: number; text: string }>) {
    await api(`/ingestion/links/${id}/transcript`, {
      method: "PUT",
      body: JSON.stringify({ language, segments }),
    });
    await refresh();
  }

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">{t("sources")}</p>
          <h1>{t("intakeTitle")}</h1>
          <p className="page-description">{t("intakeIntro")}</p>
        </div>
      </header>
      {can("researcher") && <IntakeForm providers={providers.data ?? []} onSubmit={submit} />}
      {can("researcher") && (
        <ProviderStatus
          providers={providers.data ?? []}
          loading={providers.isLoading}
          onPreflight={async () => {
            // Turning the flag on changes the query key, which is what fetches the
            // preflight result. Calling refetch() here would re-run the *previous* key,
            // because the state update has not been applied yet.
            if (!preflight) {
              setPreflight(true);
              return;
            }
            await providers.refetch();
          }}
        />
      )}
      <ReviewBacklog
        backlog={backlog.data}
        loading={backlog.isLoading}
        canApprove={can("owner")}
        onBulkReview={bulkReview}
      />
      <SubmissionList
        items={inbox.data ?? []}
        loading={inbox.isLoading}
        error={inbox.error?.message ?? null}
        onAction={action}
        onTranscript={saveTranscript}
        canWrite={can("researcher")}
        canApprove={can("owner")}
      />
    </>
  );
}
