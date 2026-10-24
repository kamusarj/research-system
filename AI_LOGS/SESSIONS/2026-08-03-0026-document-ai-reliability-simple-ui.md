# Session Log

## Context

- User request: fix the live `Request failed (500)` from selected-text document AI and simplify the
  Document workspace UI by removing nonessential content.
- Agent: Codex
- Date/time: 2026-08-03 00:26 +07

## Work Done

- Files changed:
  - Reliability: `apps/web/next.config.ts`, `apps/api/app/services/document_instant_edit.py`,
    `apps/web/hooks/use-document-instant-edit.ts`,
    `apps/web/components/document-instant-edit-feedback.tsx`.
  - Simplified UI: `apps/web/app/documents/page.tsx`, `apps/web/components/document-authoring.tsx`,
    `apps/web/components/document-brainstorm.tsx`, `apps/web/components/document-source-viewer.tsx`,
    `apps/web/app/globals.css`, `apps/web/lib/i18n.tsx`.
  - Proof: `apps/api/tests/test_document_instant_edit.py`,
    `apps/web/components/document-authoring.test.tsx`,
    `apps/web/hooks/use-document-instant-edit.test.ts`, `apps/web/lib/next-config.test.ts`,
    `apps/web/e2e/document-upload.spec.ts`.
  - Governance: decision 0028, `docs/stories/document-ai-edit-reliability/`, implementation plan and
    required `AI_LOGS` files.
- Behavior changed:
  - Next.js proxy budget increased from its 30-second default to 125 seconds, beyond the API's
    120-second provider deadline.
  - Malformed provider list/object access becomes typed HTTP 502; transient errors show localized
    copy and explicit Retry. No-change/auth/rate-limit failures are specific and nontechnical.
  - Authoring is editor-led; preview and binary upload are collapsed, while required modes and
    existing document list remain.
- Commands run:
  - Required startup reads, `bash scripts/bootstrap-harness.sh`, intake #39, intervention #8,
    decision/story creation and matrix queries.
  - Focused/full Ruff, Pytest, ESLint, TypeScript, Vitest, Next production build and Playwright.
  - Rebuilt Compose API/worker/frontend on host ports `18000`/`13000`.
  - Direct/proxied health, readiness, real proxied DeepSeek edit, Chrome screenshot, log scan and
    `git diff --check`.

## Reasoning / Decisions

- Decision: align the proxy budget instead of reducing provider time or moving one stateless edit to
  a background job.
- Reason: the API successfully completed the reported operation; the 500 was generated solely by an
  earlier intermediary timeout.
- Decision: keep Retry manual and only for transient classes.
- Reason: a provider call can cost money, and automatic duplication is not acceptable.
- Alternatives considered: 30-second provider cutoff, automatic retry, removing preview entirely,
  or asynchronous job orchestration; all were rejected or deferred for the reasons in decision 0028.

## Verification

- Tests/checks: Ruff and 295 backend tests; ESLint, TypeScript and 99 frontend tests; 14-route build;
  9/9 desktop/tablet/mobile E2E; 1920×1080 Chrome inspection; actual DeepSeek call through frontend
  proxy; runtime readiness/log scan; `git diff --check`; Harness story completion.
- Result: all final checks pass. Real proxied edit returned HTTP 200 in 13,820 ms. Runtime is healthy,
  graph validation remains 45 nodes / 32 edges, and no recent socket reset/untyped 500 appears.
  Harness story completion passed and detailed trace #45 meets the high-risk tier 3/3 requirement.
- Known issues: provider latency is still externally variable; the UI now waits through the bounded
  deadline and offers explicit Retry for a genuine transient failure. PDF/DOCX remain read-only.

## Next Agent Notes

- Continue from: owner can retest at `http://localhost:13000/documents`; the page is rebuilt and live.
- Watch out for: keep proxy timeout above, not below, the API AI deadline; never auto-retry costed AI
  calls or remove Raw/Preview/Side-by-side modes.
- Suggested next command: `docker compose logs --since=5m api frontend | rg -i 'socket hang up|500'`.
