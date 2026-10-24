# Session: Route Document Chat Edits to Review

## Context

- User request: direct edit instructions entered in contextual document chat must change the
  document through an AI proposal and show Accept/Reject, not return explanatory brainstorm prose.
- Agent: Codex
- Date/time: 2026-08-04 16:59 Asia/Bangkok

## Work Done

- Files changed: `apps/web/components/document-brainstorm.tsx`,
  `apps/web/components/document-authoring.tsx`, `apps/web/components/document-ai-editor.tsx`,
  `apps/web/components/document-instant-edit-feedback.tsx`,
  `apps/web/components/document-authoring.test.tsx`,
  `apps/web/components/document-ai-editor.test.tsx`, `apps/web/e2e/document-upload.spec.ts`,
  `apps/web/lib/i18n.tsx`, `README.md`, `Docs/Research System Implementation Plan.md`,
  `docs/stories/document-chat-edit-intent/*`,
  `docs/decisions/0032-route-document-chat-edit-intent.md`, `AI_LOGS/HANDOFF.md`,
  `AI_LOGS/TASKS.md`, `AI_LOGS/DECISIONS.md`, and this session log.
- Behavior changed: direct Vietnamese/English edit imperatives in contextual chat route to the
  existing custom instant-edit endpoint. Selection wins; otherwise bounded whole source is used.
  Full diff scrolls into view, Reject preserves source and Accept updates only the local cached
  draft. Non-edit questions stay advisory Brainstorm.
- Commands run: Harness bootstrap/intake #49/story/DEC-045; focused component tests; lint;
  TypeScript; frontend rebuild; live Chrome deterministic routing/Reject/Accept and scroll proof;
  real DeepSeek LaTeX rename smoke; backend/Ruff/frontend full/build/Playwright story proof;
  Compose, health, logs and whitespace checks.

## Reasoning / Decisions

- Decision: use deterministic mutation verbs and reuse the existing revision/range-bound instant
  edit rather than parsing free-form brainstorm output or making a second intent-classifier call.
- Reason: this gives one provider call, structured replacement text and the already accepted
  conflict/review boundary.
- Alternatives considered: provider intent classification, parsing advisory Markdown and keeping
  only generic Replace/Insert/Append were rejected. DEC-045 records the durable behavior.

## Verification

- Tests/checks: focused authoring/uploaded-editor 17/17; backend instant edit + brainstorm 11/11 and
  Ruff; full frontend 106/106; ESLint; TypeScript; 14-route build; Playwright 12/12 across
  desktop/tablet/mobile; deterministic live Chrome and real DeepSeek smoke.
- Result: live Chrome made one edit call and zero brainstorm calls; Original/Proposed and both
  decisions were visible; Reject retained `NGUYỄN MINH AN`; Accept changed it to
  `BÙI HOÀNG LINH`. A long-source Chrome fixture automatically scrolled the review into the
  viewport. Real DeepSeek returned HTTP 200 in 11.4 seconds with a complete LaTeX replacement and
  `auto_apply_allowed=false`. Story is implemented with all proof flags passing. Intervention #17
  records the owner correction and detailed trace #54 scores 3/3.

## Known Issues

- The first focused run after adding auto-scroll exposed that jsdom does not implement
  `scrollIntoView`; the browser-safe capability check removed the unhandled test error and the
  rerun passed.
- Deterministic intent routing covers supported Vietnamese/English imperative prefixes. Ambiguous
  conversational wording remains advisory by design; users can begin with `sửa`, `thay`, `đổi`,
  `edit`, `replace`, `rename`, or another documented mutation verb to request a patch.
- Existing locally inserted advisory prose shown in the owner's screenshot was not automatically
  deleted because it is user draft data; the user may undo/edit it or issue a new reviewed command.

## Next Best Action

The owner can refresh and resend `sửa tên thành Bùi Hoàng Linh`; the full patch should scroll into
view and wait for Accept or Reject.
