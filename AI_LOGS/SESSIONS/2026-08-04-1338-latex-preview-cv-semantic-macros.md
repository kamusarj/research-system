# Session Log

## Context

- User request: Fix the remaining CV-template LaTeX commands visible in Preview.
- Agent: Codex
- Date/time: 2026-08-04 13:38 ICT

## Work Done

- Files changed: `apps/web/components/document-source-viewer.tsx`, its unit test, document
  Playwright coverage, the semantic-preview story and AI handoff logs.
- Behavior changed: CV section, job-heading and list-control macros now map to semantic readable
  preview elements instead of raw source strings.
- Commands run: bootstrap Harness; intake #45 / intervention #14 / trace #51; focused unit, lint, TypeScript and E2E checks;
  direct Chrome visual proof; full frontend tests, production build and full document Playwright.

## Reasoning / Decisions

- Decision: Map known semantic CV macros explicitly; retain the safe browser-only renderer.
- Reason: Removing them loses useful hierarchy, while compiling arbitrary user TeX remains a
  separate hardened-service problem.

## Verification

- Tests/checks: 103 frontend tests, ESLint, TypeScript, Next.js build (14 routes), 12/12 document
  Playwright cases and direct Chrome visual inspection.
- Result: All pass. Preview shows clean work-experience sections, role metadata and bullets with no
  remaining macro names from the reported template.

## Next Agent Notes

- Continue from: Completed semantic CV macro correction.
- Watch out for: Unknown custom TeX commands must be handled as an explicit safe mapping, not
  executed or rendered literally.
- Suggested next command: `git diff --check`
