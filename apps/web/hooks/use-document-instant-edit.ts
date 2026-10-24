"use client";

import { useRef, useState } from "react";
import {
  applyDocumentInstantPatch,
  snapshotDocumentSelection,
  undoDocumentInstantPatch,
  type AppliedDocumentInstantEdit,
  type DocumentEditRange,
  type DocumentInstantEditSnapshot,
} from "@/lib/document-instant-edit";
import { requestDocumentInstantEdit } from "@/lib/documents";
import { ApiError } from "@/lib/api";
import type { DocumentInstantEditAction, DocumentInstantEditPatch } from "@/lib/types";

export type PendingDocumentInstantEdit = {
  snapshot: DocumentInstantEditSnapshot;
  patch: DocumentInstantEditPatch;
};

type RetryInput = {
  range: DocumentEditRange;
  action: DocumentInstantEditAction;
  instruction?: string;
};

export function instantEditFailure(reason: unknown): { key: string; retryable: boolean } {
  if (reason instanceof ApiError) {
    if (reason.code === "AI_EDIT_NO_CHANGE") {
      return { key: "instantEditNoChange", retryable: false };
    }
    if (reason.code === "AI_PROVIDER_AUTH_FAILED") {
      return { key: "instantEditProviderAuthFailed", retryable: false };
    }
    if (reason.code === "AI_PROVIDER_RATE_LIMITED" || reason.status === 429) {
      return { key: "instantEditProviderRateLimited", retryable: false };
    }
    if (reason.code === "AI_RESPONSE_INVALID") {
      return { key: "instantEditInvalidResponse", retryable: true };
    }
    if (
      reason.code === "AI_PROVIDER_UNAVAILABLE"
      || [500, 502, 503, 504].includes(reason.status)
    ) {
      return { key: "instantEditTemporaryFailure", retryable: true };
    }
    return { key: "instantEditFailed", retryable: false };
  }
  if (reason instanceof TypeError) {
    return { key: "instantEditTemporaryFailure", retryable: true };
  }
  return { key: "instantEditFailed", retryable: false };
}

export function useDocumentInstantEdit({
  source,
  sourceFormat,
  onSourceChange,
  onApplied,
}: {
  source: string;
  sourceFormat: string;
  onSourceChange: (source: string) => void;
  onApplied?: (start: number, end: number) => void;
}) {
  const sourceRef = useRef(source);
  sourceRef.current = source;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingDocumentInstantEdit | null>(null);
  const [lastChange, setLastChange] = useState<AppliedDocumentInstantEdit | null>(null);
  const [showDiff, setShowDiff] = useState(false);
  const retryRef = useRef<RetryInput | null>(null);
  const [canRetry, setCanRetry] = useState(false);

  function commit(snapshot: DocumentInstantEditSnapshot, patch: DocumentInstantEditPatch) {
    const result = applyDocumentInstantPatch(sourceRef.current, snapshot, patch);
    if (!result.ok) {
      setError(
        result.reason === "stale"
          ? "instantEditStale"
          : result.reason === "format"
            ? "instantEditInvalidResponse"
            : "instantEditInvalid",
      );
      setPending(null);
      return false;
    }
    sourceRef.current = result.source;
    onSourceChange(result.source);
    setLastChange(result.change);
    setPending(null);
    setShowDiff(false);
    setError(null);
    retryRef.current = null;
    setCanRetry(false);
    onApplied?.(result.change.start, result.change.start + result.change.replacementText.length);
    return true;
  }

  async function run(
    range: DocumentEditRange,
    action: DocumentInstantEditAction,
    instruction?: string,
  ): Promise<boolean> {
    const requestSource = sourceRef.current;
    const snapshot = snapshotDocumentSelection(requestSource, range);
    if (!snapshot || busy) {
      if (!snapshot) setError("instantEditSelectionRequired");
      return false;
    }
    setBusy(true);
    setError(null);
    setCanRetry(false);
    setPending(null);
    try {
      const patch = await requestDocumentInstantEdit({
        source: requestSource,
        sourceRevision: snapshot.sourceRevision,
        selectionStart: snapshot.range.start,
        selectionEnd: snapshot.range.end,
        action,
        instruction,
        sourceFormat,
      });
      const preview = applyDocumentInstantPatch(sourceRef.current, snapshot, patch);
      if (!preview.ok) {
        setError(
          preview.reason === "stale"
            ? "instantEditStale"
            : preview.reason === "format"
              ? "instantEditInvalidResponse"
              : "instantEditInvalid",
        );
        setPending(null);
        return false;
      }
      setPending({ snapshot, patch });
      return true;
    } catch (reason) {
      const failure = instantEditFailure(reason);
      setError(failure.key);
      retryRef.current = failure.retryable ? { range, action, instruction } : null;
      setCanRetry(failure.retryable);
      return false;
    } finally {
      setBusy(false);
    }
  }

  function applyPending() {
    if (pending) commit(pending.snapshot, pending.patch);
  }

  function discardPending() {
    setPending(null);
    setError(null);
  }

  function undo() {
    if (!lastChange) return;
    const result = undoDocumentInstantPatch(sourceRef.current, lastChange);
    if (!result.ok) {
      setError("instantEditUndoStale");
      return;
    }
    sourceRef.current = result.source;
    onSourceChange(result.source);
    onApplied?.(lastChange.start, lastChange.start + lastChange.originalText.length);
    setLastChange(null);
    setShowDiff(false);
    setError(null);
  }

  function reset() {
    setPending(null);
    setLastChange(null);
    setShowDiff(false);
    setError(null);
    retryRef.current = null;
    setCanRetry(false);
  }

  function retry() {
    const input = retryRef.current;
    if (!input || busy) return;
    void run(input.range, input.action, input.instruction);
  }

  return {
    busy,
    error,
    canRetry,
    pending,
    lastChange,
    showDiff,
    run,
    applyPending,
    discardPending,
    undo,
    reset,
    retry,
    toggleDiff: () => setShowDiff((value) => !value),
  };
}
