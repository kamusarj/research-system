"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  DocumentBrainstorm,
  type DocumentBrainstormApplyMode,
  type DocumentBrainstormHandle,
  type DocumentChatEditResult,
} from "@/components/document-brainstorm";
import { DocumentFocusWindow } from "@/components/document-focus-window";
import { DocumentOriginalViewer, DocumentPreview } from "@/components/document-source-viewer";
import {
  SelectionActionPopover,
  type SelectionAnchor,
  textareaSelectionAnchor,
} from "@/components/selection-action-popover";
import { useDocumentInstantEdit } from "@/hooks/use-document-instant-edit";
import { api } from "@/lib/api";
import {
  isStandaloneLatexDocument,
  normalizeDocumentSelection,
  paragraphRangeAtCursor,
} from "@/lib/document-instant-edit";
import {
  clearDocumentEditorDraft,
  documentEditorDraftStorageKey,
  readDocumentEditorDraft,
  rebuildDocumentRag,
  restoreDocumentSource,
  saveDocumentSource,
  writeDocumentEditorDraft,
} from "@/lib/documents";
import { useI18n } from "@/lib/i18n";
import type {
  DocumentContent,
  DocumentInstantEditAction,
  DocumentSourceVersionList,
  DocumentWorkspace,
} from "@/lib/types";

type EditorMode = "edit" | "preview" | "split";
type SelectionRange = { start: number; end: number };

const activeStatuses = new Set([
  "uploaded",
  "queued",
  "processing",
  "extracting",
  "evaluating",
  "graph_building",
]);

export function DocumentAIEditor({
  workspace,
  content,
  userId,
  canEdit,
  onChanged,
}: {
  workspace: DocumentWorkspace;
  content: DocumentContent;
  userId: string;
  canEdit: boolean;
  onChanged: () => Promise<void> | void;
}) {
  const { t } = useI18n();
  const [mode, setMode] = useState<EditorMode>("split");
  const [baseVersion, setBaseVersion] = useState(content.source_version);
  const [source, setSource] = useState(content.source_text ?? "");
  const [selection, setSelection] = useState<SelectionRange | null>(null);
  const [cursorPosition, setCursorPosition] = useState(0);
  const [selectionAnchor, setSelectionAnchor] = useState<SelectionAnchor | null>(null);
  const [focusOpen, setFocusOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState<DocumentInstantEditAction | "focus" | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cacheState, setCacheState] = useState<"restored" | "saved" | "error" | null>(null);
  const editorRef = useRef<HTMLTextAreaElement | null>(null);
  const focusEditorRef = useRef<HTMLTextAreaElement | null>(null);
  const brainstormRef = useRef<DocumentBrainstormHandle | null>(null);
  const loadedKey = useRef<string | null>(null);
  const processing = activeStatuses.has(workspace.processing_status);
  const cacheKey = useMemo(
    () => documentEditorDraftStorageKey(userId, workspace.id, baseVersion),
    [userId, workspace.id, baseVersion],
  );
  const versions = useQuery({
    queryKey: ["document-source-versions", workspace.id, workspace.source_version],
    queryFn: () => api<DocumentSourceVersionList>(`/documents/${workspace.id}/versions`),
  });

  useEffect(() => {
    const nextKey = documentEditorDraftStorageKey(
      userId,
      workspace.id,
      content.source_version,
    );
    if (loadedKey.current === nextKey) return;
    const cached = readDocumentEditorDraft(window.localStorage, nextKey);
    setBaseVersion(content.source_version);
    setSource(cached?.content ?? content.source_text ?? "");
    setCacheState(cached ? "restored" : null);
    setSelection(null);
    setCursorPosition(0);
    setSelectionAnchor(null);
    loadedKey.current = nextKey;
  }, [content.source_text, content.source_version, userId, workspace.id]);

  const canonicalSource = content.source_text ?? "";
  const dirty = source !== canonicalSource || baseVersion !== content.source_version;
  const previewContent = { ...content, source_text: source, extracted_text: source };

  function updateSource(value: string) {
    setSource(value);
    setSelection((current) => normalizeDocumentSelection(value, current));
    setCursorPosition((current) => Math.min(current, value.length));
    const saved = writeDocumentEditorDraft(window.localStorage, cacheKey, value);
    setCacheState(saved ? "saved" : "error");
  }

  function captureSelection(target: HTMLTextAreaElement) {
    setCursorPosition(target.selectionEnd);
    if (target.selectionEnd > target.selectionStart) {
      setSelection({ start: target.selectionStart, end: target.selectionEnd });
      setSelectionAnchor(textareaSelectionAnchor(target, target.selectionEnd));
    } else {
      setSelection(null);
      setSelectionAnchor(null);
    }
  }

  function applyBrainstorm(content: string, mode: DocumentBrainstormApplyMode) {
    if (!canEdit || processing || instantEdit.busy || instantEdit.pending) return;
    const activeSelection = normalizeDocumentSelection(source, selection);
    const start = mode === "append"
      ? source.length
      : mode === "replace" && activeSelection
        ? activeSelection.start
        : Math.min(cursorPosition, source.length);
    const end = mode === "replace" && activeSelection ? activeSelection.end : start;
    const separator = mode === "append" && source && !source.endsWith("\n") ? "\n\n" : "";
    const inserted = `${separator}${content}`;
    const next = source.slice(0, start) + inserted + source.slice(end);
    if (isStandaloneLatexDocument(source) && !isStandaloneLatexDocument(next)) {
      setError(t("documentBrainstormLatexApplyBlocked"));
      return;
    }
    updateSource(next);
    setCursorPosition(start + inserted.length);
    setSelection(null);
    setSelectionAnchor(null);
    requestAnimationFrame(() => {
      activeEditor()?.focus();
      activeEditor()?.setSelectionRange(start + inserted.length, start + inserted.length);
    });
  }

  function focusRange(start: number, end: number) {
    setSelection({ start, end });
    setCursorPosition(end);
    setSelectionAnchor(null);
    requestAnimationFrame(() => {
      activeEditor()?.focus();
      activeEditor()?.setSelectionRange(start, end);
    });
  }

  const instantEdit = useDocumentInstantEdit({
    source,
    sourceFormat: content.format,
    onSourceChange: updateSource,
    onApplied: focusRange,
  });

  async function runChatEdit(
    instruction: string,
    action: DocumentInstantEditAction = "custom",
  ): Promise<DocumentChatEditResult> {
    if (!canEdit || processing) return "failed";
    if (instantEdit.busy || instantEdit.pending) return "busy";
    const range = normalizeDocumentSelection(
      source,
      selection ?? { start: 0, end: source.length },
    );
    if (!range || range.end - range.start > 20_000) return "selection_required";
    setSelectionAnchor(null);
    return (await instantEdit.run(range, action, instruction)) ? "ready" : "failed";
  }

  function openParagraphInstruction() {
    if (!canEdit || processing) return;
    const range = selection ?? paragraphRangeAtCursor(source, cursorPosition);
    if (!range) return;
    focusRange(range.start, range.end);
    setSelectionAnchor(null);
    setPendingAction("focus");
    setFocusOpen(true);
  }

  function activeEditor() {
    return focusOpen ? focusEditorRef.current : editorRef.current;
  }

  function closeFocusWindow() {
    setFocusOpen(false);
    setSelectionAnchor(null);
    instantEdit.discardPending();
  }

  useEffect(() => {
    if (!focusOpen || !pendingAction) return;
    const action = pendingAction;
    setPendingAction(null);
    if (action === "focus") {
      brainstormRef.current?.focusComposer();
    } else {
      void brainstormRef.current?.runSelectionEdit(action);
    }
  }, [focusOpen, pendingAction]);

  async function save() {
    setBusy("save");
    setError(null);
    try {
      const version = await saveDocumentSource(
        workspace.id,
        baseVersion,
        source,
        t("manualDocumentEdit"),
      );
      clearDocumentEditorDraft(window.localStorage, cacheKey);
      setBaseVersion(version.version_number);
      setCacheState(null);
      instantEdit.reset();
      await onChanged();
      await versions.refetch();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("actionFailed"));
    } finally {
      setBusy(null);
    }
  }

  async function restore(versionNumber: number) {
    setBusy(`restore-${versionNumber}`);
    setError(null);
    try {
      const version = await restoreDocumentSource(workspace.id, versionNumber, baseVersion);
      clearDocumentEditorDraft(window.localStorage, cacheKey);
      setBaseVersion(version.version_number);
      setCacheState(null);
      instantEdit.reset();
      await onChanged();
      await versions.refetch();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("actionFailed"));
    } finally {
      setBusy(null);
    }
  }

  async function rebuildRag() {
    setBusy("rag");
    setError(null);
    try {
      await rebuildDocumentRag(workspace.id);
      await onChanged();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("actionFailed"));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="card document-source-panel document-ai-editor">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">{t("aiDocumentEditor")}</p>
          <h2>{t("sourceAndPreview")}</h2>
          <p className="muted">{t("aiDocumentEditorHint")}</p>
        </div>
        <div className="source-view-switcher" aria-label={t("documentViewMode")}>
          {(["edit", "preview", "split"] as EditorMode[]).map((item) => (
            <button
              type="button"
              key={item}
              className={mode === item ? "active" : ""}
              aria-pressed={mode === item}
              onClick={() => setMode(item)}
            >
              {t(`documentEditorMode.${item}`)}
            </button>
          ))}
        </div>
      </div>

      <div className="document-editor-status-row">
        <span className={`rag-state rag-${workspace.rag_status}`}>
          RAG: {t(`status.${workspace.rag_status}`)} · {workspace.rag_chunk_count} {t("chunks")}
        </span>
        <span>{t("sourceVersion")} {baseVersion}</span>
        {cacheState && (
          <span className={`draft-cache-state ${cacheState === "error" ? "error" : ""}`}>
            {t(cacheState === "restored" ? "editorDraftRestored" : cacheState === "saved" ? "draftSavedLocally" : "draftCacheUnavailable")}
          </span>
        )}
        {workspace.rag_status === "failed" && canEdit && (
          <button type="button" className="text-link" onClick={rebuildRag} disabled={Boolean(busy)}>
            {busy === "rag" ? t("rebuildingRag") : t("retryRag")}
          </button>
        )}
      </div>

      {processing && <p className="notice">{t("documentProcessingEditLocked")}</p>}
      {error && <p className="notice error-notice" role="alert">{error}</p>}
      {content.editing_representation === "extracted_text" && (
        <div className="notice document-derivative-notice">
          <strong>{t("editingExtractedText")}</strong>
          <p>{t("editingExtractedTextHint")}</p>
        </div>
      )}
      <DocumentOriginalViewer content={content} />

      <div className="document-editor-workbench">
        <div className={`document-editor-grid mode-${mode}`}>
          {(mode === "edit" || mode === "split") && (
            <article className="document-editor-pane">
              <div className="document-editor-pane-title">
                <strong>{t("rawSource")}</strong>
                <div>
                  <span>{source.length.toLocaleString("vi-VN")} {t("characters")}</span>
                  {canEdit && !processing && (
                    <button type="button" className="text-link" onClick={openParagraphInstruction}>
                      ✦ {t("editSelectionOrParagraph")}
                    </button>
                  )}
                </div>
              </div>
              <div className="document-editor-textarea-wrap">
                <textarea
                  ref={editorRef}
                  className="document-source-editor"
                  aria-label={t("documentBody")}
                  value={source}
                  readOnly={!canEdit || processing}
                  onChange={(event) => updateSource(event.target.value)}
                  onSelect={(event) => captureSelection(event.currentTarget)}
                  onMouseUp={(event) => captureSelection(event.currentTarget)}
                  onKeyUp={(event) => captureSelection(event.currentTarget)}
                  spellCheck
                />
              </div>
            </article>
          )}
          {(mode === "preview" || mode === "split") && (
            <article className="source-preview-pane">
              <div className="document-editor-pane-title"><strong>{t("formattedPreview")}</strong></div>
              <div className="document-rendered-preview">
                <div className="document-preview-paper"><DocumentPreview content={previewContent} /></div>
              </div>
            </article>
          )}
        </div>
      </div>

      {selection && selectionAnchor && canEdit && !processing && !instantEdit.busy && !instantEdit.pending && (
        <SelectionActionPopover
          anchor={selectionAnchor}
          label={t("aiEditSelection")}
          onDismiss={() => setSelectionAnchor(null)}
        >
          {(["improve", "shorten", "expand", "fix_grammar"] as DocumentInstantEditAction[]).map((action) => (
            <button
              key={action}
              type="button"
              disabled={Boolean(busy)}
              onClick={() => {
                setSelectionAnchor(null);
                setPendingAction(action);
                setFocusOpen(true);
              }}
            >
              {t(`aiEditAction.${action}`)}
            </button>
          ))}
          <button
            type="button"
            className="primary"
            disabled={Boolean(busy)}
            onClick={() => {
              setSelectionAnchor(null);
              setPendingAction("focus");
              setFocusOpen(true);
            }}
          >
            ✦ {t("askAiToEdit")}
          </button>
        </SelectionActionPopover>
      )}

      <div className="document-editor-footer">
        <p className="muted">{t("editorCachePrivacy")}</p>
        <button type="button" onClick={() => void save()} disabled={!canEdit || processing || !dirty || Boolean(busy)}>
          {busy === "save" ? t("saving") : t("saveNewVersion")}
        </button>
      </div>

      <details className="document-version-history">
        <summary>{t("versionHistory")} ({versions.data?.total ?? 0})</summary>
        <div>
          {versions.data?.items.map((version) => (
            <article key={version.id}>
              <div>
                <strong>v{version.version_number}</strong>
                <span>{t(`documentVersionOrigin.${version.origin}`)}</span>
                <small>{new Date(version.created_at).toLocaleString("vi-VN")}</small>
              </div>
              <p>{version.change_summary || "—"}</p>
              {!version.current && canEdit && !processing && (
                <button type="button" className="secondary" disabled={Boolean(busy)} onClick={() => void restore(version.version_number)}>
                  {busy === `restore-${version.version_number}` ? t("restoring") : t("restoreVersion")}
                </button>
              )}
            </article>
          ))}
        </div>
      </details>

      <DocumentFocusWindow
        open={focusOpen}
        title={t("documentFocusWindow")}
        onClose={closeFocusWindow}
        left={
          <textarea
            ref={focusEditorRef}
            className="document-focus-window-editor"
            aria-label={t("documentWindowBody")}
            value={source}
            readOnly={!canEdit || processing}
            onChange={(event) => updateSource(event.target.value)}
            onSelect={(event) => captureSelection(event.currentTarget)}
            onMouseUp={(event) => captureSelection(event.currentTarget)}
            onKeyUp={(event) => captureSelection(event.currentTarget)}
            spellCheck
          />
        }
        right={
          <DocumentBrainstorm
            ref={brainstormRef}
            source={source}
            selection={normalizeDocumentSelection(source, selection)}
            disabled={!canEdit || instantEdit.busy}
            applyDisabled={processing || Boolean(instantEdit.pending)}
            historyKey={cacheKey}
            onApply={applyBrainstorm}
            onEditInstruction={runChatEdit}
            editBusy={instantEdit.busy}
            editError={instantEdit.error}
            editCanRetry={instantEdit.canRetry}
            editPending={instantEdit.pending}
            editLastChange={instantEdit.lastChange}
            editShowDiff={instantEdit.showDiff}
            onApplyPending={instantEdit.applyPending}
            onDiscardPending={instantEdit.discardPending}
            onUndoEdit={instantEdit.undo}
            onToggleEditDiff={instantEdit.toggleDiff}
            onRetryEdit={instantEdit.retry}
          />
        }
      />
    </section>
  );
}
