# Session Log

## Context

- User request: restructure the Document workspace UI flow — initial view shows only the document
  content; selecting text shows the option popover; clicking an option switches to a two-pane window
  (left: text, right: chatbot) with an X to exit; edits persist after exit; the chatbot pane has an
  option showing the Q&A history list.
- Agent: OpenCode
- Date/time: 2026-08-07 ~16:40

## Work Done

- Files changed:
  - `apps/web/components/document-focus-window.tsx` (new): full-screen portal dialog — header with
    title + ✕ close, Escape-close, body scroll lock, two panes (left text / right chat), responsive
    stacking below 1024px.
  - `apps/web/components/document-brainstorm.tsx`: added `historyKey` prop, `BrainstormSession`
    type, `readBrainstormSessions`/`writeBrainstormSessions` helpers, per-document localStorage
    persistence (capped 20), latest-session auto-load on mount, "Chat history" toggle in the header
    with session list, "New chat" and session reload; grid rows updated for the history panel.
  - `apps/web/components/document-authoring.tsx`: removed inline brainstorm panel; selection popover
    options/Ask AI set `pendingAction` + open the window; `activeEditor()` picks the main vs window
    textarea; window left pane textarea bound to `draft.content`.
  - `apps/web/components/document-ai-editor.tsx`: same flow changes for uploaded documents.
  - `apps/web/lib/i18n.tsx`: new EN/VI keys — `chatHistory`, `chatHistoryEmpty`,
    `chatMessagesCount`, `closeFocusWindow`, `documentFocusWindow`, `documentWindowBody`,
    `documentWindowChat`.
  - `apps/web/app/globals.css`: `.document-focus-window*`, `.document-brainstorm-history*`,
    `.document-brainstorm-header-actions`, popover z-index 180→340, brainstorm grid rows.
  - Tests: `document-authoring.test.tsx` (17, +2 new: window open/close keeps edits; chat history
    persists), `document-ai-editor.test.tsx` (5) — chat tests now open the window via Ask AI.
  - Harness: intake #56, story `US-DOCUMENT-FOCUS-EDIT-WINDOW` (complete, pass), DEC-051 +
    `docs/decisions/0038-focus-edit-window-and-chat-history.md`.

## Reasoning / Decisions

- Decision: replace the always-visible brainstorm panel with an on-demand `DocumentFocusWindow`;
  selection popover actions set `pendingAction` and the window's mount effect routes them into the
  chat (`runSelectionEdit`) or focuses the composer ("Ask AI"); the left-pane textarea binds to the
  same source state so edits persist when closing; chat history is persisted per document to
  localStorage and browsed via a "Chat history" toggle.
- Reason: matches the owner's requested ChatGPT-Canvas-like flow while preserving DEC-039/045/046/049
  Accept/Reject review semantics inside the chat.
- Alternatives considered: route change (loses context), inline two-pane workbench (still cluttered),
  session-based history without persistence (fails "lịch sử hỏi đáp").

## Verification

- Tests/checks: `npx vitest run` → 115/115 pass (28 files); `npx tsc --noEmit` clean; `npx eslint`
  on changed files clean; `harness-cli story complete US-DOCUMENT-FOCUS-EDIT-WINDOW` → pass.
- Frontend image rebuilt/recreated: `docker compose up -d --build frontend`; `/documents` 200, API
  health 200 on `13000`/`18000`.
- Known issues: none. History is best-effort (storage full → silently skipped).

## Next Agent Notes

- Continue from: `US-DOCUMENT-FOCUS-EDIT-WINDOW` complete; DEC-051 recorded.
- Watch out for: disk free tight (~12G); full API rebuild with TeX may fail — prune build cache first.
- Suggested next command: open `http://localhost:13000/documents` (hard refresh), select text →
  Improve → two-pane window opens; edit, close with ✕, confirm text persisted; reopen → History list.
