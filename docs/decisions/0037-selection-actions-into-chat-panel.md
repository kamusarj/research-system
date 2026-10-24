# 0037 Route Document Selection Actions into the Brainstorm Chat Panel

Date: 2026-08-07

## Status

Accepted and implemented locally; UI-only change. Intake #55, story `US-DOCUMENT-SELECTION-CHAT-ROUTING`.

## Context

Owner asked that clicking a selection-action option in the Document workspace surface inside the adjacent
brainstorm chat tab instead of popping a new chat/review area below the editor (or, alternatively, behave
like ChatGPT Canvas editing). Previously the floating selection popover ran instant edit directly and the
review card (`DocumentInstantEditFeedback`) rendered below the textarea.

## Decision

- `DocumentBrainstorm` becomes `forwardRef`-based with a `DocumentBrainstormHandle` exposing
  `runSelectionEdit(action)` and `focusComposer()`.
- Selection popover options (`improve`, `shorten`, `expand`, `fix_grammar`) post a user message into the
  chat panel and run the same reviewed instant-edit pipeline; the reviewed card (original vs proposed diff
  with Accept/Reject, applied card with Undo, errors with Retry) renders inside the chat message thread.
- "Ask AI" and the pane-title "Edit selection or paragraph" buttons dismiss the popover and focus the chat
  composer; the old below-editor `document-custom-ai` input is removed.
- `DocumentInstantEditFeedback` is no longer rendered below the textarea in `DocumentAuthoring` or
  `DocumentAIEditor`; parents pass the instant-edit state and handlers into `DocumentBrainstorm` instead.
- The chat scrolls to the newest message and review card automatically.

## Consequences

- All AI editing review happens in one place: the chat panel next to the editor, matching the requested
  ChatGPT-Canvas-like flow.
- Predefined actions send the localized label as `instruction`; the backend still maps non-`custom`
  actions through `ACTION_INSTRUCTIONS`, so behavior is unchanged.
- No API, schema, persistence, RAG or graph contract changes; focused frontend suites remain green.
