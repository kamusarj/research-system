# Validation

## Proof Strategy

Prove both absence and non-regression: the ORM and migrated schema omit all six
tables, former HTTP routes return `404`, the newest migration downgrades and
reapplies, and all unrelated backend/frontend tests and the production build
continue to pass.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Backend and frontend suites contain no Training Data implementation dependency. |
| Integration | Alembic head matches ORM; newest migration reverses/reapplies; former API route is `404`. |
| E2E | Workspace route smoke list excludes `/training`; frontend build has no `/training` route. |
| Platform | Compose rebuild applies the migration; database has none of the six tables. |
| Performance | Not applicable. |
| Logs/Audit | Migration version and Harness trace record deletion without copying row content. |

## Fixtures

- Fresh SQLite migration database.
- Existing local PostgreSQL database with one example, one dataset, and one
  membership row.

## Commands

```text
cd apps/api && .venv/bin/ruff check app tests
cd apps/api && .venv/bin/pytest -q
cd apps/web && npm test -- --run
cd apps/web && npm run build
docker compose up -d --build api worker frontend
curl -i http://localhost:18000/api/v1/training/examples
curl -i http://localhost:13000/training
```

## Acceptance Evidence

- Ruff passes for the backend, tests, and retirement migration.
- All 256 backend tests pass, including full SQLite migration-chain,
  ORM-parity, newest-downgrade, and reapply coverage.
- All 71 frontend tests pass.
- The production frontend build succeeds with 14 routes and no `/training`
  route.
- PostgreSQL migrated to `e1f7a9c3b205`; none of the six retired tables
  remain.
- The rebuilt runtime returns `404` for both
  `/api/v1/training/examples` and `/training`; OpenAPI contains zero retired
  paths and the not-found page contains zero Training Data labels.
- API health is `ok`; API, worker, frontend, and PostgreSQL are running on the
  existing `18000`/`13000` port override.
