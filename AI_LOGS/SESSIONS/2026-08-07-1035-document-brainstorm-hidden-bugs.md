# Session: Document Brainstorm Hidden Bugs

## Context

- User request: run Harness, find hidden Document Brainstorm bugs, and fix them while keeping manual
  edit plus AI chat edit.
- Agent: OpenCode (grok-4.5)
- Date/time: 2026-08-07 10:35 Asia/Bangkok

## Work Done

- Files changed:
  - `apps/web/lib/document-instant-edit.ts`
  - `apps/web/hooks/use-document-instant-edit.ts`
  - `apps/web/components/document-brainstorm.tsx`
  - `apps/web/components/document-authoring.tsx`
  - `apps/web/components/document-ai-editor.tsx`
  - `apps/web/lib/i18n.tsx`
  - `apps/web/lib/document-instant-edit.test.ts`
  - `apps/web/components/document-authoring.test.tsx`
  - `apps/web/components/document-ai-editor.test.tsx`
  - `docs/stories/document-brainstorm-hidden-bugs/*`
  - `docs/decisions/0036-document-brainstorm-concurrency-and-latex-apply.md`
  - `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, `AI_LOGS/DECISIONS.md`, this session log
- Behavior changed: safer concurrent edit/apply, selection normalize, chat edit status feedback,
  LaTeX advisory-apply guard. Accept/Reject and manual editing preserved.
- Commands run: harness bootstrap/intake #53/story complete; focused frontend tests; ESLint; tsc;
  backend document brainstorm + instant-edit pytest.

## Reasoning / Decisions

- Decision: DEC-049 browser-boundary harden without new API contracts.
- Reason: existing suite was green but missing concurrency/selection/LaTeX-apply edge cases the owner
  still hit in practice.
- Alternatives considered: auto-Accept chat edits (rejected); provider intent classifier (rejected).

## Verification

- Tests/checks: frontend focused 27/27; ESLint; TypeScript; backend document tests 20/20;
  `harness-cli story complete US-DOCUMENT-BRAINSTORM-HIDDEN-BUGS` pass.
- Result: story implemented.

## Known Issues

- Ambiguous non-imperative chat wording still stays advisory by design.
- PDF/DOCX remain non-editable.
- No live Chrome/DeepSeek smoke in this session (deterministic unit coverage only).

## Next Best Action

- Rebuild frontend container if runtime is stale, then smoke: chat `sửa tên...` → Accept, and try
  Append advisory prose into a standalone LaTeX CV (should block).
