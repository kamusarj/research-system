"use client";

import { useEffect, useRef } from "react";
import type { AppliedDocumentInstantEdit } from "@/lib/document-instant-edit";
import type { PendingDocumentInstantEdit } from "@/hooks/use-document-instant-edit";
import { useI18n } from "@/lib/i18n";

export function DocumentInstantEditFeedback({
  busy,
  error,
  pending,
  lastChange,
  showDiff,
  onApplyPending,
  onDiscardPending,
  onUndo,
  onToggleDiff,
  canRetry,
  onRetry,
}: {
  busy: boolean;
  error: string | null;
  pending: PendingDocumentInstantEdit | null;
  lastChange: AppliedDocumentInstantEdit | null;
  showDiff: boolean;
  onApplyPending: () => void;
  onDiscardPending: () => void;
  onUndo: () => void;
  onToggleDiff: () => void;
  canRetry: boolean;
  onRetry: () => void;
}) {
  const { t } = useI18n();
  const warnings = pending?.patch.warnings ?? lastChange?.warnings ?? [];
  const feedbackRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!pending) return;
    requestAnimationFrame(() => {
      const target = feedbackRef.current;
      if (typeof target?.scrollIntoView === "function") {
        target.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    });
  }, [pending]);

  return (
    <div ref={feedbackRef} className="document-instant-edit-feedback" aria-live="polite">
      {busy && (
        <p className="document-instant-edit-progress">
          <span className="spinner" />
          <span>{t("instantEditWorking")}</span>
        </p>
      )}
      {error && (
        <div className="document-instant-edit-error notice error-notice" role="alert">
          <span>{t(error)}</span>
          {canRetry && <button type="button" className="secondary" onClick={onRetry}>{t("retry")}</button>}
        </div>
      )}
      {pending && (
        <article className="document-instant-edit-review">
          <div className="document-instant-edit-review-head">
            <p className="eyebrow">{t("instantEditReviewRequired")}</p>
            <strong>{pending.patch.explanation || t("instantEditReviewHint")}</strong>
          </div>
          {warnings.length > 0 && (
            <ul>{warnings.map((warning) => <li key={warning}>{t(`instantEditWarning.${warning}`)}</li>)}</ul>
          )}
          <div className="document-instant-edit-diff">
            <div className="document-instant-edit-diff-original">
              <strong>− {t("originalText")}</strong>
              <pre>{pending.snapshot.originalText}</pre>
            </div>
            <div className="document-instant-edit-diff-proposed">
              <strong>+ {t("proposedText")}</strong>
              <pre>{pending.patch.replacement_text}</pre>
            </div>
          </div>
          <div className="document-instant-edit-actions actions">
            <button type="button" onClick={onApplyPending}>{t("acceptAiEdit")}</button>
            <button type="button" className="secondary" onClick={onDiscardPending}>{t("rejectAiEdit")}</button>
          </div>
        </article>
      )}
      {lastChange && (
        <article className="document-instant-edit-applied">
          <div className="document-instant-edit-applied-head">
            <strong>✦ {t("instantEditApplied")}</strong>
            {lastChange.explanation && <span>{lastChange.explanation}</span>}
          </div>
          <div className="document-instant-edit-actions actions">
            <button type="button" className="secondary" onClick={onUndo}>{t("undoInstantEdit")}</button>
            <button type="button" className="text-link" onClick={onToggleDiff}>
              {t(showDiff ? "hideInstantEditDiff" : "viewInstantEditDiff")}
            </button>
          </div>
          {showDiff && (
            <div className="document-instant-edit-diff">
              <div className="document-instant-edit-diff-original">
                <strong>− {t("originalText")}</strong>
                <pre>{lastChange.originalText}</pre>
              </div>
              <div className="document-instant-edit-diff-proposed">
                <strong>+ {t("proposedText")}</strong>
                <pre>{lastChange.replacementText}</pre>
              </div>
            </div>
          )}
        </article>
      )}
    </div>
  );
}
