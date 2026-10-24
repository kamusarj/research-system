# Session Log

## Context

- User request: fully stabilize and refactor the Research System URL-to-knowledge pipeline and replace the AI/neon frontend with a professional productivity interface; verify real source classes, failure isolation, clean startup, tests and documentation.
- Agent: Codex
- Date/time: 2026-07-15 17:15 Asia/Bangkok

## Work Done

- Files changed:
  - Pipeline/domain: `apps/api/app/services/sources/`, `schemas/source.py`, `services/ingestion.py`, `models.py`, `core/config.py`, `main.py`, `worker.py`, `services/ai.py`, ingestion API/schema and migration `73f6a8c1d2e0_refactor_intake_pipeline_state.py`.
  - Tests/dependencies: API source/ingestion/research tests and `apps/api/pyproject.toml`.
  - Frontend: dashboard, shell, intake, research library, neutral global styling, graph theme, API proxy, bilingual copy, source types/detection, favicon, Vitest/Playwright configuration and tests.
  - Runtime/docs: `.env.example`, `.gitignore`, `docker-compose.yml`, `README.md`, Research System Completion Plan, `AI_LOGS/DECISIONS.md`, `HANDOFF.md`, and `TASKS.md`.
  - Preserved unrelated concurrent Discord/gap/graph changes and its separate session log; they were not reverted or attributed to this session.
- Behavior changed:
  - Every URL now follows observable normalize/detect/validate/fetch/extract/analyze/persist stages with independent human-review state.
  - Added typed, bounded adapters for GitHub repository/file/issue/pull request, public Facebook metadata, papers, direct PDFs and generic pages.
  - Added safe redirect validation, SSRF prevention, streaming byte/page limits, request and durable-job retries, content deduplication, typed errors and partial-success limitations.
  - Added multi-URL intake, source/status filters, per-row progress/error/retry/review controls and a restrained responsive workspace visual system.
- Commands run:
  - API: `.venv/bin/python -m pytest`, `.venv/bin/python -m ruff check .`, Alembic upgrade/downgrade/upgrade on SQLite, and PostgreSQL `alembic current`.
  - Web: `npm install`, `npm test`, `npm run lint`, `npm run typecheck`, `npm run build`, and `E2E_BASE_URL=http://localhost:13000 npm run test:e2e`.
  - Runtime: Compose build/up/ps/log inspection; live API submissions for invalid/private, GitHub, Facebook, article, paper/DOI and PDF URLs; a separate fresh-volume Compose project; `docker compose config -q`; `git diff --check`.

## Reasoning / Decisions

- Decision: separate finite machine-processing stages from human review state and store an explicit limitation on useful incomplete extraction.
- Reason: overloaded legacy statuses hid failure location, made retry behavior unclear and forced the UI to infer whether a record was reviewable.
- Alternatives considered: retaining source-specific status names or presenting metadata-only extraction as success. Rejected because both weaken observability and make cross-source UI behavior inconsistent.
- Decision recorded as `DEC-013`.

## Verification

- Tests/checks:
  - Backend: 34 Pytest tests and Ruff.
  - Frontend: 12 Vitest tests, ESLint, TypeScript, Next.js production build, and 6 Playwright tests across desktop/tablet.
  - Runtime: main stack health/proxy, mixed real-source jobs, browser console/network monitoring, and clean project startup from empty volumes.
- Result: all checks passed. The only test warning is the existing FastAPI/Starlette TestClient deprecation notice. The clean project migrated to `73f6a8c1d2e0` and processed `https://example.com/` from `pending` to `completed`; its containers and volumes were removed afterward.

## Known Issues

- OCR, JS browser rendering, private/region-locked Facebook access and paywalled full text are not implemented. The pipeline reports typed errors or `partial_success` and does not bypass access controls.
- Paper adapters expose available PDF URLs but do not automatically fetch full text from an abstract/DOI page; direct PDF URLs are fully supported within configured limits.
- Neo4j remains an explicit unimplemented projection adapter. Default host port 8000 is occupied by an unrelated project, so the current Research System stack uses 18000/13000.

## Next Agent Notes

- Continue from: product-owner acceptance, then receipt/occurrence and attachment-storage design for the future Discord adapter.
- Watch out for: preserve the concurrent Discord/gap/graph changes and do not store secrets or private source content in logs.
- Suggested next command: `docker compose ps && make test && make lint && make build`.
