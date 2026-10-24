# Session Log

## Context

- User request: Fix the remaining LaTeX syntax shown in the Preview and verify it in the browser.
- Agent: Codex
- Date/time: 2026-08-04 13:10 ICT

## Work Done

- Files changed:
  - `apps/web/components/document-source-viewer.tsx`
  - `apps/web/components/document-source-viewer.test.tsx`
  - `apps/web/e2e/document-upload.spec.ts`
  - `docs/stories/latex-preview-layout-macros.md`
  - `AI_LOGS/HANDOFF.md`
  - `AI_LOGS/TASKS.md`
- Behavior changed: Safe LaTeX Preview now keeps visible CV content but drops body-level layout
  syntax for custom sections, font/color declarations, spacing, minipages and alignment.
- Commands run: bootstrap Harness; Harness intake #44 / intervention #13 / trace #50; focused unit test; ESLint; TypeScript;
  full frontend test suite; frontend production build; focused and full document Playwright runs;
  direct Chrome check using an owner-style LaTeX fixture.

## Reasoning / Decisions

- Decision: Extend the safe browser parser instead of introducing a TeX runtime.
- Reason: The API container has no TeX engine. Executing user LaTeX would require a separately
  hardened compiler service and is not needed to prevent syntax leaking into the readable preview.
- Alternatives considered: Full XeLaTeX/PDF compilation remains a separate high-risk feature.

## Verification

- Tests/checks: 102 frontend unit tests; ESLint; TypeScript; Next.js build (14 routes); 12/12
  document Playwright cases across desktop/tablet/mobile; direct Chrome visual inspection.
- Result: All pass. Chrome preview showed only readable CV content and no residual layout macro
  names. `git diff --check` passed; the Harness story was verified and completed.

## Next Agent Notes

- Continue from: Completed safe-preview correction.
- Watch out for: Preview is not a TeX compiler. New custom semantic macros should receive a
  targeted safe-parser mapping and test rather than be rendered literally.
- Suggested next command: `git diff --check`
