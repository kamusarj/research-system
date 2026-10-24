# Session Log

## Context

- User request: route document selection-action options into the adjacent brainstorm chat tab instead
  of popping a new chat/review area below the editor (or behave like ChatGPT Canvas editing).
- Agent: OpenCode
- Date/time: 2026-08-07 ~13:30

## Work Done

- Files changed:
  - `apps/web/components/document-brainstorm.tsx` — converted to `forwardRef` with
    `DocumentBrainstormHandle { runSelectionEdit, focusComposer }`; added edit-state props
    (`editBusy`, `editError`, `editCanRetry`, `editPending`, `editLastChange`, `editShowDiff`) and
    handlers (`onApplyPending`, `onDiscardPending`, `onUndoEdit`, `onToggleEditDiff`, `onRetryEdit`);
    renders `DocumentInstantEditFeedback` inside the chat thread as an `edit-review` assistant
    message; auto-scrolls the messages container; `onEditInstruction` accepts an optional action.
  - `apps/web/components/document-authoring.tsx` — removed below-editor `DocumentInstantEditFeedback`
    and the `document-custom-ai` input; popover buttons call `brainstormRef.runSelectionEdit(action)`;
    "Ask AI" and pane-title edit button call `focusComposer()`; `runChatEdit` accepts an action;
    removed `runInstantEdit`/`customOpen`/`instruction` state.
  - `apps/web/components/document-ai-editor.tsx` — same routing changes.
  - `apps/web/lib/i18n.tsx` — updated `documentChatEditReady`/`documentChatEditFailed` texts (EN/VI)
    to point at the chat panel.
  - `apps/web/app/globals.css` — removed `.document-custom-ai` rules; added
    `.document-brainstorm-message.edit-review` styles (flat margins, single-column diff).
  - `apps/web/components/document-authoring.test.tsx` — new test asserting the selection action posts
    a user message in the chat and the review card lives inside the brainstorm aside.
  - Harness: intake #55, story `US-DOCUMENT-SELECTION-CHAT-ROUTING` (complete, pass),
    `DEC-050` + `docs/decisions/0037-selection-actions-into-chat-panel.md`.
- Behavior changed: selection popover actions surface in the chat panel (ChatGPT-Canvas-like);
  review/accept/reject/undo/retry all happen in the chat; no review card below the editor.

## Reasoning / Decisions

- Decision: route popover actions through the existing reviewed instant-edit pipeline but render the
  review card inside `DocumentBrainstorm`; custom instructions go through the chat composer.
- Reason: keeps DEC-039/045/046/049 review-before-apply semantics while matching the owner's requested
  UI flow and the ChatGPT Canvas pattern.
- Alternatives considered: lifting chat messages state into parents (too invasive); a standalone
  floating review widget (violates "in the chat tab"); imperative handle chosen instead.

## Verification

- Tests/checks: `npx vitest run components/document-authoring.test.tsx components/document-ai-editor.test.tsx`
  → 20/20 pass (incl. new routing test); `npx tsc --noEmit` clean; `npx eslint` on changed files clean;
  `harness-cli story complete US-DOCUMENT-SELECTION-CHAT-ROUTING` → pass (ran verify command).
- Frontend image rebuilt and recreated: `docker compose up -d --build frontend`; `GET /documents` 200,
  API health 200 on `18000`/`13000`.
- Known issues: none. `.document-instant-edit-feedback` component file kept (used inside the chat).

## Next Agent Notes

- Continue from: `US-DOCUMENT-SELECTION-CHAT-ROUTING` complete; DEC-050 recorded.
- Watch out for: disk free is tight (~12G); full API/worker rebuild with TeX may fail — use
  `docker builder prune` if needed.
- Suggested next command: open `http://localhost:13000/documents` (hard refresh) and try selecting
  text → Improve → review card appears in the chat panel.
