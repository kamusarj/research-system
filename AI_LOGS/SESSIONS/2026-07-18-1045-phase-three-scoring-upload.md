# Session Log

## Context

- User request: Continue with the next implementation step for the Business AI Agents knowledge-graph upgrade.
- Agent: Codex.
- Date/time: 2026-07-18 10:45 +0700.

## Work Done

- Files changed:
  - `apps/api/app/schemas/paper_fit.py`
  - `apps/api/app/services/paper_fit.py`
  - `apps/api/tests/test_paper_fit.py`
  - `apps/api/tests/fixtures/paper_fit_gold_v1.json`
  - `apps/api/app/models.py`
  - `apps/api/migrations/versions/a4f1c7d9e205_add_document_workspace_and_evaluation.py`
  - `apps/api/app/services/object_storage.py`
  - `apps/api/app/services/documents.py`
  - `apps/api/app/schemas/documents.py`
  - `apps/api/app/api/documents.py`
  - `apps/api/app/api/router.py`
  - `apps/api/app/core/config.py`
  - `apps/api/app/main.py`
  - `apps/api/app/schemas/research.py`
  - `apps/api/pyproject.toml`
  - `apps/api/tests/test_documents.py`
  - `apps/web/app/documents/page.tsx`
  - `apps/web/app/documents/page.test.tsx`
  - `apps/web/lib/documents.ts`
  - `apps/web/lib/documents.test.ts`
  - `apps/web/lib/types.ts`
  - `apps/web/lib/i18n.tsx`
  - `apps/web/components/app-shell.tsx`
  - `apps/web/app/globals.css`
  - `apps/web/e2e/document-upload.spec.ts`
  - `apps/web/e2e/research-workspace.spec.ts`
  - `.env.example`
  - `docker-compose.yml`
  - `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
  - `AI_LOGS/HANDOFF.md`
  - `AI_LOGS/TASKS.md`
- Behavior changed:
  - Added server-owned paper-fit hard gates, exact weighted scoring and deterministic routing at 40/60/80.
  - Added a versioned 30-paper gold set with 10 core, 10 enabling, 5 tangential and 5 irrelevant fixtures.
  - Added a local object-storage interface with atomic writes, SHA-256 hashing and configurable 20 MB streaming limit.
  - Added PDF/Markdown/plain-text validation, duplicate-content protection and transactional creation of draft research, attachment and document-workspace records.
  - Added upload/list/detail/download document APIs without exposing internal storage paths.
  - Added the bilingual `/documents` upload/library UI and responsive navigation/test coverage.
  - Added a named Compose volume shared by API and worker for document objects.
- Commands run:
  - `uv run --extra dev python -m pytest -q tests/test_paper_fit.py tests/test_documents.py`
  - `uv run --extra dev python -m pytest -q`
  - `uv run --extra dev python -m ruff check app tests`
  - `npm run lint`
  - `npm run typecheck`
  - `npm run test -- --run`
  - `npm run build`
  - Alembic upgrade/downgrade/upgrade against a temporary SQLite database.
  - Mocked Playwright document-upload scenario on desktop, tablet and mobile.
  - `docker compose config -q`
  - `git diff --check`

## Reasoning / Decisions

- Decision: Keep scoring and routing deterministic in the backend; the future AI provider supplies structured dimension evidence but cannot supply an authoritative final score.
- Reason: This makes threshold behavior reproducible, testable and independent of model/provider drift.
- Decision: A failed hard gate has no fit score and cannot proceed as a misleading low-scored paper.
- Reason: Unreadable, duplicate or otherwise invalid inputs should be explicitly rejected before semantic scoring.
- Decision: Store uploaded bytes behind an `ObjectStorage` protocol and keep paths out of API responses.
- Reason: The local adapter supports the MVP while preserving an upgrade path to MinIO/S3 without coupling domain logic to the filesystem.
- Decision: Upload creates only draft metadata and an isolated workspace in `uploaded` state.
- Reason: Extraction, AI evaluation, document graph generation and canonical graph mutation must remain reviewable later stages; no upload may auto-publish.

## Verification

- Tests/checks:
  - Backend: 62 Pytest tests and Ruff.
  - Frontend: ESLint, TypeScript, 17 Vitest tests and Next.js production build.
  - Migration: `a4f1c7d9e205` upgrade/downgrade/upgrade.
  - E2E: mocked document upload on three viewports.
  - Compose config and diff whitespace checks.
- Result: All checks passed. Pytest reports only the existing Starlette/httpx deprecation warning. The running Docker stack was not rebuilt.

## Known Issues

- Uploaded workspaces remain `uploaded`; durable worker extraction and AI evaluation are not implemented yet.
- Document nodes, edges, evidence locations and mapping change sets are not implemented yet.
- Local storage is the accepted MVP adapter; MinIO/S3 remains a later production upgrade.

## Next Agent Notes

- Continue from: build durable workspace job stages for extraction and provider-neutral paper evaluation, then persist the evaluation record.
- Watch out for: never trust provider-calculated totals, never expose storage paths, never auto-publish AI output, and preserve typed failure/limitation states.
- Suggested next command: `cd apps/api && uv run --extra dev python -m pytest -q tests/test_documents.py tests/test_paper_fit.py`.
