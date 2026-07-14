# Session Log

## Context

- User request: read the project AI logs and continue implementation.
- Agent: Codex.
- Date/time: 2026-07-13 22:45 +07.

## Work Done

- Files changed: intake API/service/models/tests, new worker module and Alembic migration, Compose, intake UI/i18n/CSS, environment example, README, completion plan, and AI logs.
- Behavior changed: link submission is now asynchronous. The API persists a queued job, a separate worker claims it with a recoverable lease, transient errors use exponential retry, and permanent/exhausted errors enter `dead-letter` with explicit manual retry.
- Commands run: required AI log/doc reads; Ruff; pytest; Alembic upgrade/downgrade/upgrade on SQLite; ESLint; Next.js production build; Compose config validation; dependency installation for the host verification environment.

## Reasoning / Decisions

- Decision: use PostgreSQL-backed durable job state before adding Redis as optional transport.
- Reason: PostgreSQL is already the source of truth and provides safe row claiming and lease recovery without expanding the local runtime dependency set.
- Alternatives considered: in-process FastAPI background tasks were rejected because they are not durable; Redis-only queue state was deferred because it would weaken the current PostgreSQL source-of-truth guarantee and add infrastructure before needed.

## Verification

- Tests/checks: Ruff pass; 14 backend tests pass; SQLite migration upgrade/downgrade/upgrade pass; Alembic has one head (`4a6e8b2c9d10`); ESLint pass; Next.js production build pass; `docker compose config -q` pass.
- Result: automated checks pass. The existing Starlette/httpx deprecation warning remains.

## Known Issues

- Docker Desktop was not running, so PostgreSQL migration/runtime smoke and the Compose worker process were not exercised in containers.
- No in-app browser session was available, so the logged visual EN/VI UX review remains open.
- Redis transport, scheduled collectors, richer PDF/GitHub extraction, auth/RBAC, MinIO and observability are still pending Gate C work.

## Next Best Action

- Start Docker, run the migration and worker smoke on ports 18000/13000, visually review the bilingual intake states, then implement PDF and GitHub-specific extractors.
