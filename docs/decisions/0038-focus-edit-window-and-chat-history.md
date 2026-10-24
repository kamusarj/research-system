# 0038 Two-Pane Focus Edit Window with Persistent Chat History

Date: 2026-08-07

## Status

Accepted and implemented locally; UI-only. Intake #56, story `US-DOCUMENT-FOCUS-EDIT-WINDOW`.

## Context

Owner asked for a ChatGPT-Canvas-like flow in the Document workspace: the initial view shows only the
document content; selecting text shows the action options; clicking an option switches the screen to a
window with two panes (left = text, right = chatbot) and an X button to exit; edits made inside persist
after exiting; the chatbot pane has an option that shows the list of past Q&A sessions.

## Decision

- `DocumentFocusWindow` (new): full-screen portal dialog with a header (title + ✕ close), Escape-close,
  body scroll lock, and two panes — left text editor, right chat. Responsive: panes stack below 1024px.
- `DocumentAuthoring` and `DocumentAIEditor` no longer render the brainstorm panel inline; the workbench
  shows only the document content. Selection popover options set a `pendingAction` and open the window;
  a mount effect routes the action into the chat (`runSelectionEdit`) or focuses the composer ("Ask AI").
- Left pane textarea binds to the same source state, so edits persist when the window closes; the
  active-editor ref switches between the main and window textareas.
- `DocumentBrainstorm` gains `historyKey`; sessions are persisted to
  `document-brainstorm-history:<key>` in localStorage (capped at 20), auto-loaded (latest session on
  open), and browsable via a "Chat history" toggle in the chat header with "New chat" and session reload.
- Selection popover z-index raised above the window so in-window selections still show options.

## Consequences

- The main document view stays clean until the user acts on a selection; all AI review happens in the
  focus window chat, preserving DEC-039/045/046/049 Accept/Reject semantics.
- Chat history is per-document and local-only; it is never sent to the provider.
- No API, schema, persistence, RAG or graph contract changes; frontend 115/115, ESLint and TypeScript
  pass; frontend image rebuilt live on `13000`.
