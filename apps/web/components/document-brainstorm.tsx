"use client";

import {
  forwardRef,
  type FormEvent,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";
import { ChatMarkdown } from "@/components/chat-markdown";
import { DocumentInstantEditFeedback } from "@/components/document-instant-edit-feedback";
import { brainstormDocument } from "@/lib/documents";
import { useI18n } from "@/lib/i18n";
import { ApiError } from "@/lib/api";
import type { AppliedDocumentInstantEdit } from "@/lib/document-instant-edit";
import type { PendingDocumentInstantEdit } from "@/hooks/use-document-instant-edit";
import type { DocumentBrainstormMessage, DocumentInstantEditAction } from "@/lib/types";

export type DocumentBrainstormApplyMode = "replace" | "insert" | "append";
export type DocumentTextSelection = { start: number; end: number };
export type DocumentChatEditResult = "ready" | "selection_required" | "failed" | "busy";

export type DocumentBrainstormHandle = {
  runSelectionEdit: (action: DocumentInstantEditAction) => Promise<void>;
  focusComposer: () => void;
};

export type BrainstormSession = {
  id: string;
  createdAt: string;
  messages: VisibleMessage[];
};

type VisibleMessage = DocumentBrainstormMessage & {
  id: string;
  truncated?: boolean;
  model?: string;
  localOnly?: boolean;
};

type RetryRequest = {
  message: string;
  history: DocumentBrainstormMessage[];
};

const DOCUMENT_EDIT_INSTRUCTION = /^(?:(?:hãy|vui lòng|làm ơn|please)\s+)?(?:sửa|thay|đổi|viết lại|chuyển|dịch|rút gọn|mở rộng|xóa|xoá|thêm|chèn|cập nhật|fix|edit|change|replace|rename|rewrite|convert|translate|shorten|expand|remove|delete|add|insert|update)\b/iu;
const HISTORY_STORAGE_PREFIX = "document-brainstorm-history:";
const MAX_HISTORY_SESSIONS = 20;

export function isDocumentEditInstruction(value: string): boolean {
  return DOCUMENT_EDIT_INSTRUCTION.test(value.trim());
}

export function brainstormHistoryStorageKey(historyKey: string): string {
  return `${HISTORY_STORAGE_PREFIX}${historyKey}`;
}

export function readBrainstormSessions(
  storage: Pick<Storage, "getItem">,
  historyKey: string,
): BrainstormSession[] {
  try {
    const raw = storage.getItem(brainstormHistoryStorageKey(historyKey));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as { sessions?: BrainstormSession[] };
    return Array.isArray(parsed?.sessions) ? parsed.sessions : [];
  } catch {
    return [];
  }
}

export function writeBrainstormSessions(
  storage: Pick<Storage, "setItem">,
  historyKey: string,
  sessions: BrainstormSession[],
): void {
  try {
    storage.setItem(
      brainstormHistoryStorageKey(historyKey),
      JSON.stringify({ sessions: sessions.slice(-MAX_HISTORY_SESSIONS) }),
    );
  } catch {
    // storage full or unavailable; history is best-effort
  }
}

export function documentBrainstormFailure(reason: unknown): {
  key: string;
  retryable: boolean;
} {
  if (reason instanceof ApiError) {
    if (reason.code === "CHAT_PROVIDER_RATE_LIMITED" || reason.status === 429) {
      return { key: "documentBrainstormRateLimited", retryable: true };
    }
    if (
      reason.code === "CHAT_PROVIDER_UNAVAILABLE"
      || [500, 502, 503, 504].includes(reason.status)
    ) {
      return { key: "documentBrainstormTemporaryFailure", retryable: true };
    }
    if (reason.code === "CHAT_PROVIDER_FAILED") {
      return { key: "documentBrainstormInvalidResponse", retryable: true };
    }
    return { key: "documentBrainstormFailed", retryable: false };
  }
  if (reason instanceof TypeError) {
    return { key: "documentBrainstormTemporaryFailure", retryable: true };
  }
  return { key: "documentBrainstormFailed", retryable: false };
}

export const DocumentBrainstorm = forwardRef<DocumentBrainstormHandle, {
  source: string;
  selection: DocumentTextSelection | null;
  disabled?: boolean;
  applyDisabled?: boolean;
  historyKey?: string;
  onApply: (content: string, mode: DocumentBrainstormApplyMode) => void;
  onEditInstruction?: (
    instruction: string,
    action?: DocumentInstantEditAction,
  ) => Promise<DocumentChatEditResult>;
  editBusy?: boolean;
  editError?: string | null;
  editCanRetry?: boolean;
  editPending?: PendingDocumentInstantEdit | null;
  editLastChange?: AppliedDocumentInstantEdit | null;
  editShowDiff?: boolean;
  onApplyPending?: () => void;
  onDiscardPending?: () => void;
  onUndoEdit?: () => void;
  onToggleEditDiff?: () => void;
  onRetryEdit?: () => void;
}>(function DocumentBrainstorm({
  source,
  selection,
  disabled = false,
  applyDisabled = false,
  historyKey,
  onApply,
  onEditInstruction,
  editBusy = false,
  editError = null,
  editCanRetry = false,
  editPending = null,
  editLastChange = null,
  editShowDiff = false,
  onApplyPending,
  onDiscardPending,
  onUndoEdit,
  onToggleEditDiff,
  onRetryEdit,
}, ref) {
  const { t } = useI18n();
  const [messages, setMessages] = useState<VisibleMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryRequest, setRetryRequest] = useState<RetryRequest | null>(null);
  const [sessions, setSessions] = useState<BrainstormSession[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const messagesRef = useRef<HTMLDivElement | null>(null);
  const composerRef = useRef<HTMLTextAreaElement | null>(null);
  const sessionIdRef = useRef<string>(`session-${Date.now()}`);
  const sessionsRef = useRef<BrainstormSession[]>([]);
  const selectedChars = selection ? selection.end - selection.start : 0;
  const history = useMemo(
    () => messages
      .filter((message) => !message.localOnly)
      .map(({ role, content }) => ({ role, content }))
      .slice(-10),
    [messages],
  );
  const locked = disabled || sending;
  const editActivity = editBusy || Boolean(editError) || Boolean(editPending) || Boolean(editLastChange);

  useEffect(() => {
    if (!historyKey) return;
    const stored = readBrainstormSessions(window.localStorage, historyKey);
    sessionsRef.current = stored;
    setSessions(stored);
    const latest = stored[stored.length - 1];
    if (latest) {
      sessionIdRef.current = latest.id;
      setMessages(latest.messages);
    }
  }, [historyKey]);

  useEffect(() => {
    if (!historyKey) return;
    const current: BrainstormSession = {
      id: sessionIdRef.current,
      createdAt: sessionsRef.current.find((session) => session.id === sessionIdRef.current)?.createdAt
        ?? new Date().toISOString(),
      messages,
    };
    const next = [
      ...sessionsRef.current.filter((session) => session.id !== current.id),
      current,
    ];
    sessionsRef.current = next;
    setSessions(next);
    writeBrainstormSessions(window.localStorage, historyKey, next);
  }, [messages, historyKey]);

  function pushLocalAssistant(content: string) {
    setMessages((current) => [
      ...current,
      {
        id: `assistant-local-${Date.now()}`,
        role: "assistant",
        content,
        localOnly: true,
      },
    ]);
  }

  function handleEditResult(result: DocumentChatEditResult) {
    if (result === "ready") {
      pushLocalAssistant(t("documentChatEditReady"));
    } else if (result === "selection_required") {
      setError("documentChatEditSelectionRequired");
    } else if (result === "busy") {
      setError("documentChatEditBusy");
    } else {
      pushLocalAssistant(t("documentChatEditFailed"));
    }
  }

  function startNewChat() {
    sessionIdRef.current = `session-${Date.now()}`;
    setMessages([]);
    setError(null);
    setRetryRequest(null);
    setHistoryOpen(false);
    setSending(false);
  }

  function loadSession(session: BrainstormSession) {
    sessionIdRef.current = session.id;
    setMessages(session.messages);
    setError(null);
    setRetryRequest(null);
    setHistoryOpen(false);
    composerRef.current?.focus();
  }

  useImperativeHandle(ref, () => ({
    async runSelectionEdit(action: DocumentInstantEditAction) {
      if (locked || !onEditInstruction) return;
      const label = t(`aiEditAction.${action}`);
      setMessages((current) => [
        ...current,
        { id: `user-${Date.now()}`, role: "user", content: label },
      ]);
      setSending(true);
      setError(null);
      setRetryRequest(null);
      try {
        handleEditResult(await onEditInstruction(label, action));
      } finally {
        setSending(false);
      }
    },
    focusComposer() {
      composerRef.current?.focus();
    },
  }));

  useEffect(() => {
    const target = messagesRef.current;
    if (target) target.scrollTop = target.scrollHeight;
  }, [messages, sending, editPending, editLastChange, editError, editBusy]);

  async function requestBrainstorm(request: RetryRequest) {
    setSending(true);
    setError(null);
    setRetryRequest(null);
    try {
      const response = await brainstormDocument({
        source,
        message: request.message,
        history: request.history,
        selection,
      });
      setMessages((current) => [
        ...current,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: response.content,
          truncated: response.source_context_truncated,
          model: response.model_name,
        },
      ]);
    } catch (reason) {
      const failure = documentBrainstormFailure(reason);
      setError(failure.key);
      setRetryRequest(failure.retryable ? request : null);
    } finally {
      setSending(false);
    }
  }

  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = input.trim();
    if (!message || !source.trim() || locked) return;
    const request = { message, history };
    setMessages((current) => [
      ...current,
      { id: `user-${Date.now()}`, role: "user", content: message },
    ]);
    setInput("");
    if (onEditInstruction && isDocumentEditInstruction(message)) {
      setSending(true);
      setError(null);
      setRetryRequest(null);
      try {
        handleEditResult(await onEditInstruction(message));
      } finally {
        setSending(false);
      }
      return;
    }
    await requestBrainstorm(request);
  }

  return (
    <aside className="document-brainstorm" aria-label={t("documentBrainstorm")}>
      <div className="document-brainstorm-header">
        <div className="document-brainstorm-title">
          <span className="document-brainstorm-mark" aria-hidden="true">✦</span>
          <div>
            <h3>{t("documentBrainstorm")}</h3>
            <p>{t("documentBrainstormHint")}</p>
          </div>
        </div>
        <div className="document-brainstorm-header-actions">
          {selectedChars > 0 && (
            <span className="document-brainstorm-selection">
              {selectedChars.toLocaleString("vi-VN")} {t("selectedCharacters")}
            </span>
          )}
          {historyKey && (
            <button
              type="button"
              className="document-brainstorm-history-toggle"
              aria-expanded={historyOpen}
              onClick={() => setHistoryOpen((value) => !value)}
            >
              {t("chatHistory")}
            </button>
          )}
        </div>
      </div>

      {historyOpen && historyKey && (
        <div className="document-brainstorm-history" aria-label={t("chatHistory")}>
          <div className="document-brainstorm-history-head">
            <strong>{t("chatHistory")}</strong>
            <button type="button" className="text-link" onClick={startNewChat}>
              {t("newChat")}
            </button>
          </div>
          {sessions.length === 0 ? (
            <p className="document-brainstorm-history-empty">{t("chatHistoryEmpty")}</p>
          ) : (
            <ul className="document-brainstorm-history-list">
              {[...sessions].reverse().map((session) => {
                const firstUser = session.messages.find((message) => message.role === "user");
                return (
                  <li key={session.id}>
                    <button type="button" onClick={() => loadSession(session)}>
                      <span className="document-brainstorm-history-date">
                        {new Date(session.createdAt).toLocaleString("vi-VN")}
                      </span>
                      <span className="document-brainstorm-history-preview">
                        {firstUser?.content || "—"}
                      </span>
                      <span className="document-brainstorm-history-count">
                        {session.messages.length} {t("chatMessagesCount")}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}

      <div className="document-brainstorm-messages" aria-live="polite" ref={messagesRef}>
        {messages.length === 0 && !editActivity && (
          <div className="document-brainstorm-empty">
            <span className="document-brainstorm-empty-icon" aria-hidden="true">✦</span>
            <p>{t("documentBrainstormEmpty")}</p>
          </div>
        )}
        {messages.map((message) => (
          <article
            className={[
              "document-brainstorm-message",
              message.role,
              message.localOnly ? "local-only" : "",
            ].filter(Boolean).join(" ")}
            key={message.id}
          >
            <div className="document-brainstorm-message-meta">
              <span className={`document-brainstorm-avatar ${message.role}`} aria-hidden="true">
                {message.role === "user" ? "U" : "AI"}
              </span>
              <strong>{message.role === "user" ? t("you") : t("brainstormAssistant")}</strong>
            </div>
            <div className="document-brainstorm-message-body">
              {message.role === "assistant"
                ? <ChatMarkdown content={message.content} />
                : <p>{message.content}</p>}
              {message.role === "assistant" && !message.localOnly && (
                <>
                  <div className="document-brainstorm-response-meta">
                    {message.model && <span>{message.model}</span>}
                    {message.truncated && <span>{t("documentContextTruncated")}</span>}
                  </div>
                  <div className="document-brainstorm-apply">
                    <button
                      type="button"
                      className="secondary"
                      disabled={!selection || locked || applyDisabled}
                      onClick={() => onApply(message.content, "replace")}
                    >
                      {t("replaceSelection")}
                    </button>
                    <button
                      type="button"
                      className="secondary"
                      disabled={locked || applyDisabled}
                      onClick={() => onApply(message.content, "insert")}
                    >
                      {t("insertAtCursor")}
                    </button>
                    <button
                      type="button"
                      className="secondary"
                      disabled={locked || applyDisabled}
                      onClick={() => onApply(message.content, "append")}
                    >
                      {t("appendToDocument")}
                    </button>
                  </div>
                </>
              )}
            </div>
          </article>
        ))}
        {editActivity && (
          <article className="document-brainstorm-message assistant edit-review">
            <div className="document-brainstorm-message-meta">
              <span className="document-brainstorm-avatar assistant" aria-hidden="true">AI</span>
              <strong>{t("brainstormAssistant")}</strong>
            </div>
            <div className="document-brainstorm-message-body">
              <DocumentInstantEditFeedback
                busy={editBusy}
                error={editError}
                canRetry={editCanRetry}
                pending={editPending}
                lastChange={editLastChange}
                showDiff={editShowDiff}
                onApplyPending={onApplyPending ?? (() => undefined)}
                onDiscardPending={onDiscardPending ?? (() => undefined)}
                onUndo={onUndoEdit ?? (() => undefined)}
                onToggleDiff={onToggleEditDiff ?? (() => undefined)}
                onRetry={onRetryEdit ?? (() => undefined)}
              />
            </div>
          </article>
        )}
        {sending && (
          <div className="document-brainstorm-thinking">
            <span className="spinner" />
            <span>{t("documentBrainstormThinking")}</span>
          </div>
        )}
      </div>

      {error && (
        <div className="notice error-notice document-brainstorm-error" role="alert">
          <span>{t(error)}</span>
          {retryRequest && (
            <button
              type="button"
              className="secondary"
              disabled={locked}
              onClick={() => void requestBrainstorm(retryRequest)}
            >
              {t("retry")}
            </button>
          )}
        </div>
      )}
      <form className="document-brainstorm-composer" onSubmit={send}>
        <label htmlFor="document-brainstorm-message">{t("chatMessage")}</label>
        <div className="document-brainstorm-composer-shell">
          <textarea
            id="document-brainstorm-message"
            ref={composerRef}
            rows={3}
            maxLength={4000}
            value={input}
            disabled={locked || !source.trim()}
            onChange={(event) => setInput(event.target.value)}
            placeholder={t("documentBrainstormPlaceholder")}
          />
          <button type="submit" disabled={locked || !source.trim() || !input.trim()}>
            {sending ? t("sending") : t("sendMessage")}
          </button>
        </div>
        <p className="document-brainstorm-privacy">{t("documentBrainstormPrivacy")}</p>
      </form>
    </aside>
  );
});
