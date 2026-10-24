# Session Log

## Context

- User request: Add direct document creation in Document workspace and cache
  unsaved text so F5 does not lose it.
- Agent: Codex
- Date/time: 2026-07-30 23:20-23:38 Asia/Bangkok

## Work Done

- Files changed:
  - Added `apps/web/components/document-authoring.tsx` and its tests.
  - Extended `apps/web/lib/documents.ts` with format mapping, safe filename
    generation and versioned per-user cache helpers.
  - Integrated authoring into `apps/web/app/documents/page.tsx`.
  - Updated source-viewer button semantics, bilingual copy, responsive styles
    and the Document workspace E2E suite.
  - Updated current product docs, Harness story/decision and AI handoff logs.
- Behavior changed:
  - Researchers can author Markdown, TXT, LaTeX, reStructuredText, AsciiDoc or
    HTML directly in Document workspace with safe live preview.
  - Unsaved edits are stored immediately in a bounded localStorage entry scoped
    to the authenticated user and restored after refresh/browser restart.
  - Creation reuses the existing governed upload pipeline. Cache survives
    server errors and clears after success or explicit discard.
- Commands run:
  - Harness bootstrap, intake #31, high-risk story and decision registration.
  - Focused and full Vitest suites.
  - ESLint, TypeScript and Next.js production build.
  - Focused backend Markdown-upload integration test through isolated `uv`.
  - Frontend image rebuild and runtime health/service checks.
  - Playwright refresh/discard test across desktop, tablet and mobile Chrome.

## Reasoning / Decisions

- Decision: use existing document upload as the canonical Create command and
  keep pre-create text in a per-user browser cache.
- Reason: this preserves storage, provenance, AI processing and review behavior
  while satisfying F5 recovery without adding a second document API/schema.
- Alternatives considered:
  - New JSON document endpoint: rejected as duplicate contract.
  - Unscoped local cache: rejected as cross-user disclosure risk.
  - Session storage: rejected because browser closure would lose local-first work.
  - Server autosave: deferred because it needs retention, authorization,
    concurrency and schema decisions.

## Verification

- Tests/checks:
  - Focused authoring/cache/source-viewer tests: 11/11 pass.
  - Full frontend: 77/77 pass.
  - ESLint: pass.
  - Sequential TypeScript: pass.
  - Next.js production build: pass, 14 routes.
  - Backend Markdown upload integration: pass.
  - Playwright F5 restoration/discard: 3/3 across desktop/tablet/mobile.
  - Runtime: `/documents` HTTP 200, API health `ok`, database/API/worker/frontend
    running on `18000/13000`.
- Result: Complete.

## Known Issues

- Running TypeScript concurrently with `next build` caused transient missing
  `.next/types` errors because both commands mutate generated files; the
  sequential rerun passed.
- The repository `apps/web/test-results` directory is root-owned, so the first
  host Playwright run could not update `.last-run.json`. The test passed with an
  isolated `/tmp` output directory without changing permissions.
- Browser localStorage is local and unencrypted; drafts do not sync between
  devices.

## Next Agent Notes

- Continue from: story `US-DOCUMENT-AUTHORING-CACHE`, decision DEC-033.
- Watch out for: do not send draft text before explicit Create or make cache
  keys global across users.
- Suggested next command:
  `E2E_BASE_URL=http://localhost:13000 npx playwright test e2e/research-workspace.spec.ts --grep 'document authoring draft survives refresh' --workers=1 --output=/tmp/document-authoring-e2e`
