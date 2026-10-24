"use client";

import { useState } from "react";
import { useI18n } from "@/lib/i18n";
import type { ReviewBacklog } from "@/lib/types";

type Props = {
  backlog: ReviewBacklog | undefined;
  canApprove: boolean;
  onBulkReview: (decision: "approve" | "reject") => Promise<void>;
  loading?: boolean;
};

/**
 * Show how much collected material is still waiting on a person.
 *
 * Sources that finish extraction but are never reviewed contribute nothing to the
 * knowledge graph. Nothing in the product used to say how many there were, so the queue
 * grew unnoticed until it held most of the library.
 */
export function ReviewBacklog({ backlog, canApprove, onBulkReview, loading = false }: Props) {
  const { t } = useI18n();
  const [working, setWorking] = useState<"approve" | "reject" | null>(null);
  const [error, setError] = useState("");

  if (!backlog) return loading ? <div className="skeleton review-backlog-skeleton" role="status" aria-label="Đang tải hàng chờ duyệt" /> : null;

  const waiting = backlog.needs_review;
  const stranded = backlog.duplicates_awaiting_original;
  if (!waiting && !stranded && !backlog.failed) return null;

  async function decide(decision: "approve" | "reject") {
    setWorking(decision);
    setError("");
    try {
      await onBulkReview(decision);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("actionFailed"));
    } finally {
      setWorking(null);
    }
  }

  return (
    <section className="card review-backlog" aria-labelledby="review-backlog-title">
      <div>
        <p className="eyebrow">{t("intakeReviewQueue")}</p>
        <h2 id="review-backlog-title">
          {t("reviewBacklogCount").replace("{count}", String(waiting))}
        </h2>
        <p className="muted">{t("reviewBacklogHint")}</p>
        <ul className="review-backlog-facts">
          {stranded > 0 && (
            <li>{t("duplicatesAwaitingOriginal").replace("{count}", String(stranded))}</li>
          )}
          {backlog.failed > 0 && (
            <li>{t("failedAwaitingRetry").replace("{count}", String(backlog.failed))}</li>
          )}
          <li>
            {t("autoApproveThreshold").replace(
              "{value}",
              String(Math.round(backlog.auto_approve_confidence * 100)),
            )}
          </li>
        </ul>
      </div>
      {canApprove && waiting > 0 && (
        <div className="review-backlog-actions">
          <button disabled={working !== null} onClick={() => decide("approve")}>
            {working === "approve" ? t("loading") : t("approveAllQueued")}
          </button>
          <button
            className="secondary"
            disabled={working !== null}
            onClick={() => decide("reject")}
          >
            {working === "reject" ? t("loading") : t("rejectAllQueued")}
          </button>
        </div>
      )}
      {error && <p className="row-error" role="alert">{error}</p>}
    </section>
  );
}
