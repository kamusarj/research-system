# Session Log

## Context

- User request: Make LaTeX Preview behave correctly like Overleaf instead of leaking template
  commands.
- Agent: Codex
- Date/time: 2026-08-04 14:24 ICT

## Work Done

- Files changed: API compiler service/route/schema/config/runtime controls/tests/Dockerfile;
  frontend PDF preview/component/styles/i18n/E2E; Compose/env/runtime docs; high-risk story,
  decision and AI logs.
- Behavior changed: standalone LaTeX drafts now compile to PDF through XeLaTeX and render inside
  the existing Preview. Safe parsed text is only the loading/error fallback.
- Commands run: Harness bootstrap/intake/story/decision/intervention #15/trace #52; focused and full backend/frontend tests;
  Ruff, ESLint, TypeScript and build; two Docker API builds/recreate; real API PDF smokes; direct
  Chrome CV compile and screenshot; document Playwright across three viewports.

## Reasoning / Decisions

- Decision: Use real bounded XeLaTeX with no shell escape; record DEC-043.
- Reason: a macro parser cannot reproduce arbitrary template layout or package behavior.
- Alternatives considered: expanding regex mappings and browser-only partial TeX engines.

## Verification

- Tests/checks: Ruff; 301 backend tests; ESLint; TypeScript; 103 frontend tests; Next.js 14-route
  build; 12/12 document E2E; Docker health; real PDF 1.7 compile; direct Chrome PDF iframe proof.
- Result: All required proof passes. One initial full pytest invocation used the pytest executable
  and hit two pre-existing package-import collection errors; the repository-compatible
  `.venv/bin/python -m pytest` command passed all 301 tests.

## Next Agent Notes

- Continue from: XeLaTeX preview is live on API 18000/frontend 13000.
- Watch out for: Current contract is standalone `.tex` only. Do not enable shell escape, external
  assets or multi-file projects without a dedicated sandbox design.
- Suggested next command: `docker compose logs --tail=50 api`
