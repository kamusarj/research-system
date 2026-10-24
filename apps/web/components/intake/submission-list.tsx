"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { StatusBadge } from "@/components/status-badge";
import { SubmissionError } from "@/components/intake/submission-error";
import { parseTranscript } from "@/lib/intake";
import { useI18n } from "@/lib/i18n";
import type { SourceKind, SourceSubmission, TranscriptSegment } from "@/lib/types";

type Action = "approve" | "reject" | "retry";

type Props = {
  items: SourceSubmission[];
  loading: boolean;
  error: string | null;
  onAction: (id: string, action: Action) => Promise<void>;
  onTranscript?: (id: string, language: string, segments: TranscriptSegment[]) => Promise<void>;
  canWrite?: boolean;
  canApprove?: boolean;
};

function TranscriptEditor({ item, onSave }: { item: SourceSubmission; onSave: NonNullable<Props["onTranscript"]> }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [language, setLanguage] = useState(item.transcript.language ?? "vi");
  const [value, setValue] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const segments = parseTranscript(value);
      setSaving(true);
      await onSave(item.id, language, segments);
      setValue("");
      setOpen(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("actionFailed"));
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <button className="secondary" onClick={() => setOpen(true)}>
        {t(item.transcript.configured ? "replaceTranscript" : "addTranscript")}
      </button>
    );
  }
  return (
    <form className="transcript-editor" onSubmit={submit}>
      <label>
        <span>{t("transcriptLanguage")}</span>
        <select value={language} onChange={(event) => setLanguage(event.target.value)}>
          <option value="vi">Tiếng Việt</option>
          <option value="en">Tiếng Anh</option>
          <option value="other">Ngôn ngữ khác</option>
        </select>
      </label>
      <label>
        <span>{t("timestampedTranscript")}</span>
        <textarea
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="00:12 Nội dung transcript"
          rows={5}
          required
        />
      </label>
      {error && <p className="row-error" role="alert">{error}</p>}
      <div className="row-actions">
        <button disabled={saving} type="submit">{t("saveTranscript")}</button>
        <button disabled={saving} type="button" className="secondary" onClick={() => setOpen(false)}>{t("cancel")}</button>
      </div>
    </form>
  );
}

export function SubmissionList({ items, loading, error, onAction, onTranscript, canWrite = true, canApprove = true }: Props) {
  const { t } = useI18n();
  const [sourceFilter, setSourceFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [workingId, setWorkingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState("");
  const filtered = useMemo(
    () => items.filter((item) => {
      const source = item.classification.normalized_source?.source_type ?? "";
      return (!sourceFilter || source === sourceFilter) && (!statusFilter || item.status === statusFilter);
    }),
    [items, sourceFilter, statusFilter],
  );

  async function action(id: string, value: Action) {
    setWorkingId(id);
    setActionError("");
    try {
      await onAction(id, value);
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : t("actionFailed"));
    } finally {
      setWorkingId(null);
    }
  }

  return (
    <section aria-labelledby="source-queue-title">
      <div className="section-heading queue-heading">
        <div>
          <h2 id="source-queue-title">{t("sourceQueue")}</h2>
          <p className="muted">{t("sourceQueueHint")}</p>
        </div>
        <span>{filtered.length}</span>
      </div>
      <div className="table-toolbar">
        <select value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value)} aria-label={t("sourceTypeFilter")}>
          <option value="">{t("allSources")}</option>
          {(["github", "facebook", "paper", "pdf", "article"] as SourceKind[]).map((kind) => (
            <option value={kind} key={kind}>{t(`sourceType.${kind}`)}</option>
          ))}
        </select>
        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} aria-label={t("statusFilter")}>
          <option value="">{t("allStatuses")}</option>
          {["pending", "processing", "fetching", "extracting", "analyzing", "completed", "partial_success", "failed"].map((status) => (
            <option value={status} key={status}>{t(`status.${status}`)}</option>
          ))}
        </select>
      </div>
      {(error || actionError) && <p className="notice error-notice" role="alert">{error || actionError}</p>}
      <div className="data-table source-table">
        <div className="table-header" aria-hidden="true">
          <span>{t("document")}</span><span>{t("source")}</span><span>{t("status")}</span><span>{t("updated")}</span><span />
        </div>
        {filtered.map((item) => {
          const normalized = item.classification.normalized_source;
          const sourceKind = normalized?.source_type ?? "article";
          const limitationCode = normalized?.limitation_code;
          // A limitation is not a failure: the source was collected, but part of it stayed
          // out of reach. Show the translated explanation when there is one.
          const translatedLimitation = limitationCode ? t(`error.${limitationCode}`) : "";
          const limitationHint = limitationCode ? t(`errorHint.${limitationCode}`) : "";
          const limitation =
            translatedLimitation && translatedLimitation !== `error.${limitationCode}`
              ? translatedLimitation
              : limitationCode || normalized?.limitation_message
                ? t("unknownLimitation")
                : "";
          const resourceKind = normalized?.metadata?.resource_kind;
          const canAddTranscript = canWrite && onTranscript && sourceKind === "facebook"
            && ["reel", "video"].includes(String(resourceKind))
            && item.review_status !== "approved" && !item.research_id;
          return (
            <article className="table-row source-row" key={item.id}>
              <div className="document-cell">
                <a href={item.url} target="_blank" rel="noreferrer" className="document-title">
                  {item.title ?? item.url}
                </a>
                <p>{item.classification.summary || item.content_preview || t("noExtractedPreview")}</p>
                {limitation && (
                  <p className="limitation">
                    {limitation}
                    {limitationHint && limitationHint !== `errorHint.${limitationCode}` && (
                      <> {limitationHint}</>
                    )}
                  </p>
                )}
                {item.review_status === "duplicate" && (
                  <p className="limitation">
                    {t("duplicateOf")}
                    {!item.research_id && <> {t("duplicateAwaitingOriginal")}</>}
                  </p>
                )}
                {item.transcript.configured && (
                  <p className="muted">{t("transcriptAttached").replace("{count}", String(item.transcript.segment_count))}</p>
                )}
                {(item.error || item.error_code) && (
                  <SubmissionError
                    code={item.error_code}
                    message={item.error}
                    details={item.error_details}
                  />
                )}
                {canAddTranscript && <TranscriptEditor item={item} onSave={onTranscript} />}
              </div>
              <div><span className={`source-kind source-${sourceKind}`}>{t(`sourceType.${sourceKind}`)}</span><small>{item.provider_name ?? "—"}</small></div>
              <div><StatusBadge status={item.status} /><small>{t(`reviewStatus.${item.review_status}`)}</small></div>
              <time dateTime={item.updated_at}>{new Date(item.updated_at).toLocaleString("vi-VN")}</time>
              <div className="row-actions">
                {canApprove && item.review_status === "needs_review" && (
                  <>
                    <button disabled={workingId === item.id} onClick={() => action(item.id, "approve")}>{t("approve")}</button>
                    <button className="secondary" disabled={workingId === item.id} onClick={() => action(item.id, "reject")}>{t("reject")}</button>
                  </>
                )}
                {canWrite && item.status === "failed" && <button disabled={workingId === item.id} onClick={() => action(item.id, "retry")}>{t("retry")}</button>}
                {item.research_id && <Link className="text-link" href={`/research/${item.research_id}`}>{t("openResearch")}</Link>}
              </div>
            </article>
          );
        })}
        {loading && <div className="table-state"><span className="spinner" />{t("loading")}</div>}
        {!loading && filtered.length === 0 && <div className="table-state"><strong>{t("noLinks")}</strong><span>{t("noLinksHint")}</span></div>}
      </div>
    </section>
  );
}
