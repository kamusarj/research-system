# Session Log

## Context

- User request: implement AI that edits a selected passage directly inside both the create-document
  editor and uploaded editable document source, after analyzing the likely edit cases.
- Agent: Codex
- Date/time: 2026-08-02 23:18 +07

## Work Done

- Files changed:
  - Backend contract and route: `apps/api/app/schemas/documents.py`,
    `apps/api/app/api/documents.py`, `apps/api/app/services/document_instant_edit.py`,
    `apps/api/app/core/runtime_controls.py`.
  - Backend proof: `apps/api/tests/test_document_instant_edit.py`, `apps/api/tests/test_auth.py`.
  - Frontend behavior: `apps/web/hooks/use-document-instant-edit.ts`,
    `apps/web/lib/document-instant-edit.ts`, `apps/web/lib/documents.ts`,
    `apps/web/lib/types.ts`, `apps/web/components/document-instant-edit-feedback.tsx`,
    `apps/web/components/document-authoring.tsx`, `apps/web/components/document-ai-editor.tsx`,
    `apps/web/lib/i18n.tsx`, `apps/web/app/globals.css`.
  - Frontend proof: `apps/web/lib/document-instant-edit.test.ts`,
    `apps/web/components/document-authoring.test.tsx`,
    `apps/web/components/document-ai-editor.test.tsx`, `apps/web/e2e/document-upload.spec.ts`.
  - Planning/governance: `docs/decisions/0027-local-instant-document-ai-patches.md`,
    `docs/stories/document-instant-ai-edit/`, `Docs/Research System Implementation Plan.md`,
    `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`, and required `AI_LOGS` files.
- Behavior changed:
  - Native selection exposes direct AI actions in new and uploaded editable documents.
  - Exact low/medium-risk prose patches auto-apply to the cached local draft with Undo/View diff.
  - Protected content and semantic changes remain review-only; stale source/selection rejects a
    response. Create/Save remains the only persistent version/RAG transition.
- Commands run:
  - `bash scripts/bootstrap-harness.sh`
  - Harness intake/decision/story creation and matrix queries.
  - `cd apps/api && uv run ruff check app tests && uv run python -m pytest -q`
  - `cd apps/web && npm run lint && npm run typecheck && npm run test -- --run && npm run build`
  - `API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 docker compose up -d --build api worker frontend`
  - Health, readiness, OpenAPI, recent-log and `git diff --check` checks.
  - `cd apps/web && E2E_BASE_URL=http://localhost:13000 npx playwright test e2e/document-upload.spec.ts --output=/tmp/document-instant-ai-edit-final`

## Reasoning / Decisions

- Decision: interpret “AI tự sửa” as mutation of the recoverable browser draft, not an unreviewed
  canonical save; this gives immediate editing without silently publishing or rebuilding RAG.
- Reason: ordinary wording changes are reversible, while facts, citations, code, formulas and
  explicit semantic changes can alter research meaning and need a review boundary.
- Alternatives considered: keep all edits as persisted proposals (too many clicks for the requested
  interaction) or auto-save every AI response (unsafe, noisy version/RAG churn).

## Verification

- Tests/checks: Ruff; 294 backend tests; ESLint; TypeScript; 94 frontend tests; 14-route production
  build; 9 Playwright cases across desktop/tablet/mobile; rebuilt runtime health/readiness/OpenAPI;
  recent log scan; `git diff --check`.
- Result: all final checks passed. API/worker/frontend are running on `18000`/`13000`, readiness is
  `ready`, and graph validation remains 45 nodes / 32 edges. Harness story
  `US-DOCUMENT-INSTANT-AI-EDIT` completed with its fresh proof command; detailed trace #44 meets
  the required high-risk tier 3/3.
- Known issues: editable source formats remain UTF-8 Markdown/TXT/LaTeX/rST/AsciiDoc/HTML. PDF and
  DOCX stay binary/read-only pending a byte-faithful rich-document editing design. Browser Undo is
  intentionally only for the latest exact patch; durable history begins at explicit Save.

## Next Agent Notes

- Continue from: the direct edit path is complete and runtime-tested; product-owner manual wording
  review can start at `http://localhost:13000/documents`.
- Watch out for: do not turn instant local edits into implicit Save/RAG mutations; preserve the
  high-risk review classification and exact-source conflict checks.
- Suggested next command: `API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 docker compose ps`.
