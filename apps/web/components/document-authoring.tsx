"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  DocumentBrainstorm,
  type DocumentBrainstormApplyMode,
  type DocumentBrainstormHandle,
  type DocumentChatEditResult,
  type DocumentTextSelection,
} from "@/components/document-brainstorm";
import { DocumentFocusWindow } from "@/components/document-focus-window";
import { DocumentSourceViewer } from "@/components/document-source-viewer";
import {
  SelectionActionPopover,
  type SelectionAnchor,
  textareaSelectionAnchor,
} from "@/components/selection-action-popover";
import { useDocumentInstantEdit } from "@/hooks/use-document-instant-edit";
import {
  isStandaloneLatexDocument,
  normalizeDocumentSelection,
  paragraphRangeAtCursor,
} from "@/lib/document-instant-edit";
import {
  DOCUMENT_AUTHOR_DRAFT_MAX_CHARS,
  DOCUMENT_AUTHORING_FORMATS,
  DOCUMENT_EDITABLE_IMPORT_ACCEPT,
  authoredDocumentFile,
  clearDocumentAuthorDraft,
  documentAuthoringFormat,
  documentDraftStorageKey,
  editableDocumentDraftFromFile,
  emptyDocumentAuthorDraft,
  readDocumentAuthorDraft,
  uploadDocument,
  writeDocumentAuthorDraft,
  type DocumentAuthorDraft,
} from "@/lib/documents";
import { useI18n } from "@/lib/i18n";
import type { DocumentContent, DocumentInstantEditAction } from "@/lib/types";

export function DocumentAuthoring({ userId }: { userId: string }) {
  const { t } = useI18n();
  const router = useRouter();
  const cacheKey = useMemo(() => documentDraftStorageKey(userId), [userId]);
  const [draft, setDraft] = useState<DocumentAuthorDraft>(emptyDocumentAuthorDraft);
  const [cacheState, setCacheState] = useState<"idle" | "restored" | "saved" | "error">("idle");
  const [creating, setCreating] = useState(false);
  const [importing, setImporting] = useState(false);
  const [selection, setSelection] = useState<DocumentTextSelection | null>(null);
  const [cursorPosition, setCursorPosition] = useState(0);
  const [selectionAnchor, setSelectionAnchor] = useState<SelectionAnchor | null>(null);
  const [focusOpen, setFocusOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState<DocumentInstantEditAction | "focus" | null>(null);
  const editorRef = useRef<HTMLTextAreaElement | null>(null);
  const focusEditorRef = useRef<HTMLTextAreaElement | null>(null);
  const brainstormRef = useRef<DocumentBrainstormHandle | null>(null);

  function activeEditor() {
    return focusOpen ? focusEditorRef.current : editorRef.current;
  }
  const [message, setMessage] = useState<{ type: "error" | "success"; text: string } | null>(
    null,
  );

  useEffect(() => {
    const cached = readDocumentAuthorDraft(window.localStorage, cacheKey);
    setDraft(cached ?? emptyDocumentAuthorDraft());
    setCacheState(cached && (cached.title || cached.content) ? "restored" : "idle");
  }, [cacheKey]);

  function updateDraft(patch: Partial<Pick<DocumentAuthorDraft, "title" | "format" | "content">>) {
    const next: DocumentAuthorDraft = {
      ...draft,
      ...patch,
      version: 1,
      updatedAt: new Date().toISOString(),
    };
    setDraft(next);
    if (patch.content !== undefined) {
      setSelection((current) => normalizeDocumentSelection(next.content, current));
      setCursorPosition((current) => Math.min(current, next.content.length));
    }
    setCacheState(
      writeDocumentAuthorDraft(window.localStorage, cacheKey, next) ? "saved" : "error",
    );
    setMessage(null);
  }

  async function importEditableSource(file: File | null) {
    if (!file) return;
    setImporting(true);
    setMessage(null);
    try {
      const imported = await editableDocumentDraftFromFile(file);
      updateDraft(imported);
      setSelection(null);
      setCursorPosition(0);
      setSelectionAnchor(null);
      instantEdit.reset();
      requestAnimationFrame(() => {
        editorRef.current?.focus();
        editorRef.current?.setSelectionRange(0, 0);
      });
    } catch (reason) {
      const code = reason instanceof Error ? reason.message : "DOCUMENT_IMPORT_FAILED";
      const key = code === "DOCUMENT_TOO_LARGE"
        ? "documentTooLarge"
        : code === "DOCUMENT_INVALID_UTF8"
          ? "documentInvalidUtf8"
          : code === "DOCUMENT_DRAFT_TOO_LARGE"
            ? "documentDraftTooLarge"
            : code === "DOCUMENT_EMPTY"
              ? "documentEmpty"
              : "documentEditableImportFailed";
      setMessage({ type: "error", text: t(key) });
    } finally {
      setImporting(false);
    }
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
    if (instantEdit.busy || instantEdit.pending) return;
    const activeSelection = normalizeDocumentSelection(draft.content, selection);
    const start = mode === "append"
      ? draft.content.length
      : mode === "replace" && activeSelection
        ? activeSelection.start
        : Math.min(cursorPosition, draft.content.length);
    const end = mode === "replace" && activeSelection ? activeSelection.end : start;
    const separator = mode === "append" && draft.content && !draft.content.endsWith("\n")
      ? "\n\n"
      : "";
    const inserted = `${separator}${content}`;
    const next = draft.content.slice(0, start) + inserted + draft.content.slice(end);
    if (isStandaloneLatexDocument(draft.content) && !isStandaloneLatexDocument(next)) {
      setMessage({ type: "error", text: t("documentBrainstormLatexApplyBlocked") });
      return;
    }
    const nextCursor = start + inserted.length;
    updateDraft({ content: next });
    setSelection(null);
    setCursorPosition(nextCursor);
    requestAnimationFrame(() => {
      activeEditor()?.focus();
      activeEditor()?.setSelectionRange(nextCursor, nextCursor);
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
    source: draft.content,
    sourceFormat: draft.format,
    onSourceChange: (content) => updateDraft({ content }),
    onApplied: focusRange,
  });

  async function runChatEdit(
    instruction: string,
    action: DocumentInstantEditAction = "custom",
  ): Promise<DocumentChatEditResult> {
    if (instantEdit.busy || instantEdit.pending) return "busy";
    const range = normalizeDocumentSelection(
      draft.content,
      selection ?? { start: 0, end: draft.content.length },
    );
    if (!range || range.end - range.start > 20_000) return "selection_required";
    setSelectionAnchor(null);
    return (await instantEdit.run(range, action, instruction)) ? "ready" : "failed";
  }

  function openParagraphInstruction() {
    const range = selection ?? paragraphRangeAtCursor(draft.content, cursorPosition);
    if (!range) return;
    focusRange(range.start, range.end);
    setSelectionAnchor(null);
    setPendingAction("focus");
    setFocusOpen(true);
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

  function closeFocusWindow() {
    setFocusOpen(false);
    setSelectionAnchor(null);
    instantEdit.discardPending();
  }

  async function create() {
    if (!draft.title.trim() || !draft.content.trim()) return;
    setCreating(true);
    setMessage(null);
    try {
      const workspace = await uploadDocument(authoredDocumentFile(draft));
      clearDocumentAuthorDraft(window.localStorage, cacheKey);
      setDraft(emptyDocumentAuthorDraft());
      setCacheState("idle");
      setMessage({ type: "success", text: t("authoredDocumentCreated") });
      instantEdit.reset();
      router.push(`/documents/${workspace.id}`);
    } catch (reason) {
      setMessage({
        type: "error",
        text: reason instanceof Error ? reason.message : t("documentUploadFailed"),
      });
    } finally {
      setCreating(false);
    }
  }

  const format = documentAuthoringFormat(draft.format);
  const preview: DocumentContent = {
    workspace_id: "local-author-draft",
    filename: `${draft.title || t("untitledDocument")}${format.extension}`,
    format: format.extension.slice(1),
    preview_kind: format.previewKind,
    source_text: draft.content,
    extracted_text: draft.content,
    supports_raw: true,
    source_truncated: false,
    editable: true,
    source_version: 1,
  };

  return (
    <section className="card document-authoring-card">
      <div className="document-authoring-heading">
        <h2>{t("createDocument")}</h2>
        <span className={`draft-cache-state quiet ${cacheState === "error" ? "error" : ""}`}>
          {cacheState === "restored"
            ? t("draftRestored")
            : cacheState === "saved"
              ? t("draftSavedLocally")
              : cacheState === "error"
                ? t("draftCacheUnavailable")
                : t("draftNotSavedYet")}
        </span>
      </div>

      <div className="document-authoring-form">
        <div className="document-authoring-meta">
          <label>
            {t("documentTitle")}
            <input
              value={draft.title}
              maxLength={180}
              onChange={(event) => updateDraft({ title: event.target.value })}
              placeholder={t("documentTitlePlaceholder")}
              required
            />
          </label>
          <label>
            {t("sourceFormat")}
            <select
              value={draft.format}
              onChange={(event) => updateDraft({
                format: event.target.value as DocumentAuthorDraft["format"],
              })}
            >
              {DOCUMENT_AUTHORING_FORMATS.map((option) => (
                <option key={option.value} value={option.value}>
                  {t(`documentFormat.${option.value}`)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="document-editable-import-row">
          <label className="secondary-link document-editable-import">
            {importing ? t("importingEditableSource") : t("importEditableSource")}
            <input
              type="file"
              accept={DOCUMENT_EDITABLE_IMPORT_ACCEPT}
              disabled={importing}
              onChange={(event) => void importEditableSource(event.target.files?.[0] ?? null)}
            />
          </label>
        </div>
        <div className="document-authoring-workbench">
          <div className="document-authoring-content-field">
            <div className="document-editor-pane-title">
              <label htmlFor="document-authoring-content">{t("documentBody")}</label>
              {draft.content && (
                <button type="button" className="text-link" onClick={openParagraphInstruction}>
                  ✦ {t("editSelectionOrParagraph")}
                </button>
              )}
            </div>
            <textarea
              id="document-authoring-content"
              ref={editorRef}
              className="document-authoring-editor"
              rows={16}
              value={draft.content}
              maxLength={DOCUMENT_AUTHOR_DRAFT_MAX_CHARS}
              onChange={(event) => updateDraft({ content: event.target.value })}
              onSelect={(event) => captureSelection(event.currentTarget)}
              onMouseUp={(event) => captureSelection(event.currentTarget)}
              onKeyUp={(event) => captureSelection(event.currentTarget)}
              placeholder={t("documentBodyPlaceholder")}
              required
            />
          </div>
        </div>
        {selection && selectionAnchor && !instantEdit.busy && !instantEdit.pending && (
          <SelectionActionPopover
            anchor={selectionAnchor}
            label={t("aiEditSelection")}
            onDismiss={() => setSelectionAnchor(null)}
          >
            {(["improve", "shorten", "expand", "fix_grammar"] as DocumentInstantEditAction[]).map((action) => (
              <button
                key={action}
                type="button"
                onClick={() => {
                  setSelectionAnchor(null);
                  setPendingAction(action);
                  setFocusOpen(true);
                }}
              >
                {t(`aiEditAction.${action}`)}
              </button>
            ))}
            <button type="button" className="primary" onClick={() => {
              setSelectionAnchor(null);
              setPendingAction("focus");
              setFocusOpen(true);
            }}>
              ✦ {t("askAiToEdit")}
            </button>
          </SelectionActionPopover>
        )}
        <div className="document-authoring-footer">
          <div className="actions">
            <button
              type="button"
              onClick={() => void create()}
              disabled={creating || !draft.title.trim() || !draft.content.trim()}
            >
              {creating ? t("creatingDocument") : t("createAuthoredDocument")}
            </button>
          </div>
        </div>
        {message && (
          <p className={`notice ${message.type === "error" ? "error-notice" : "document-success"}`}>
            {message.text}
          </p>
        )}
      </div>

      {draft.content && <DocumentSourceViewer content={preview} collapsible />}

      <DocumentFocusWindow
        open={focusOpen}
        title={t("documentFocusWindow")}
        onClose={closeFocusWindow}
        left={
          <textarea
            id="document-focus-content"
            ref={focusEditorRef}
            className="document-focus-window-editor"
            aria-label={t("documentWindowBody")}
            value={draft.content}
            maxLength={DOCUMENT_AUTHOR_DRAFT_MAX_CHARS}
            onChange={(event) => updateDraft({ content: event.target.value })}
            onSelect={(event) => captureSelection(event.currentTarget)}
            onMouseUp={(event) => captureSelection(event.currentTarget)}
            onKeyUp={(event) => captureSelection(event.currentTarget)}
            placeholder={t("documentBodyPlaceholder")}
            spellCheck
          />
        }
        right={
          <DocumentBrainstorm
            ref={brainstormRef}
            source={draft.content}
            selection={normalizeDocumentSelection(draft.content, selection)}
            disabled={instantEdit.busy}
            applyDisabled={Boolean(instantEdit.pending)}
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
