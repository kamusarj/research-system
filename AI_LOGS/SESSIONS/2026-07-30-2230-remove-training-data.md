# Session Log

## Context

- User request: Remove everything related to Training Data.
- Agent: Codex
- Date/time: 2026-07-30 21:55-22:30 Asia/Bangkok

## Work Done

- Files changed:
  - Removed `apps/web/app/training/page.tsx`.
  - Removed `apps/api/app/api/training.py`,
    `apps/api/app/schemas/training.py`, and
    `apps/api/tests/test_training.py`.
  - Removed Training Data router/RBAC/model/seed code from
    `apps/api/app/api/router.py`, `apps/api/app/core/auth.py`,
    `apps/api/app/models.py`, and `apps/api/app/seed.py`.
  - Added destructive migration
    `apps/api/migrations/versions/e1f7a9c3b205_remove_training_data_hub.py`.
  - Removed frontend copy/smoke coverage from `apps/web/lib/i18n.tsx`,
    `apps/web/e2e/research-workspace.spec.ts`, and
    `apps/web/components/app-shell.test.tsx`.
  - Updated `README.md`, `AGENTS.md`, the MVP specification, implementation
    plan, Harness story/decision, and AI handoff records.
- Behavior changed:
  - `/training` and all `/api/v1/training/*` routes are retired.
  - Six Training Data tables and their rows are absent from the active schema.
  - Current product documentation no longer plans or advertises the feature.
- Commands run:
  - Harness bootstrap, intake #30, high-risk story and decision registration.
  - Read-only PostgreSQL table/count inventory before deletion.
  - `uv run --isolated --all-extras ruff check ...`
  - `PYTHONPATH=. uv run --isolated --all-extras pytest -q`
  - `npm test -- --run`
  - `npm run build`
  - Alembic head/upgrade/check and newest migration reverse/reapply through tests.
  - `docker compose exec -T api alembic upgrade head`
  - Rebuilt and recreated API, worker and frontend.
  - Runtime health, retired-route 404, OpenAPI absence and PostgreSQL table-absence checks.

## Reasoning / Decisions

- Decision: remove the active feature and persisted domain while preserving
  immutable migration/log/source history.
- Reason: the owner explicitly authorized destructive removal; keeping dormant
  APIs or tables would not satisfy the request, while rewriting historical
  migrations would make existing upgrades unsafe.
- Alternatives considered:
  - Hide only the UI: rejected because API/data would remain.
  - Keep empty dormant tables: rejected because the domain is retired.
  - Export a backup: rejected because it would retain data the owner requested
    to delete.
  - Rewrite historical migrations/logs: rejected because it destroys auditability.

## Verification

- Tests/checks:
  - Ruff: pass.
  - Backend: 256/256 pass.
  - Frontend: 71/71 pass.
  - Next.js production build: pass, 14 routes, no `/training`.
  - Migration chain/ORM parity/latest downgrade-reapply: pass.
  - PostgreSQL head: `e1f7a9c3b205`; retired table count: 0.
  - Runtime: API health `ok`; retired API and page both return 404; OpenAPI
    retired-path count 0; API/worker/frontend/database are running.
- Result: Complete. The three existing relationship/domain rows and all six
  Training Data tables were deleted without affecting other product domains.

## Known Issues

- The checked-in `apps/api/.venv` points to an obsolete absolute Python path.
  Verification used an isolated `uv` environment instead.
- Port `8000` remains occupied by another project, so this stack continues on
  API `18000` and frontend `13000`.
- Historical migrations, prior AI logs, decisions and original brainstorm
  sources still mention the retired feature by design as audit history.

## Next Agent Notes

- Continue from: migration `e1f7a9c3b205` and decision DEC-032.
- Watch out for: do not restore Training Data routes/tables from historical
  source documents.
- Suggested next command:
  `docker compose exec -T api alembic current && curl --fail http://localhost:18000/api/v1/health`
