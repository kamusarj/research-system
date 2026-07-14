# Session Log

## Context

- User request: kiểm tra AI logs và tiến trình dự án; nếu có log thì tiếp tục các bước theo plan.
- Agent: Codex.
- Date/time: 2026-07-13 00:14 +07.

## Work Done

- Files changed: gap model/schema/service/API/migration/tests under `apps/api`; `/gaps` workspace, navigation/dashboard/styles under `apps/web`; `docker-compose.yml`, `README.md`, implementation plan, and AI logs.
- Behavior changed: Phase 8 now detects and persists low-coverage concept gaps, supports prioritize/assign/dismiss/snooze, creates provenance-linked deep-research drafts, and blocks approval until human review. Docker port overrides now configure CORS, and `.next` uses a named volume.
- Commands run: required log/docs inspection; `make test`, `make lint`, `make build`; Alembic upgrade/downgrade/upgrade on temporary SQLite; Alembic upgrade on PostgreSQL; Compose config, seed and smoke checks; Markdown fence checks.

## Reasoning / Decisions

- Decision: implement graph low-coverage as detector v1 and keep detection an explicit POST action.
- Reason: KB/search/graph passed the existing regression suite, satisfying the plan gate for beginning Phase 8 while keeping the projection local-first and rebuildable.
- Alternatives considered: autonomous deep research, trend ingestion and scheduled digest were deferred because they require broader signals/workers and are not needed for the first reviewable workflow.

## Verification

- Tests/checks: 9 backend tests, Ruff, ESLint, Next.js production build with 9 routes, SQLite and PostgreSQL migrations, `docker compose config -q`, API health/detection/CORS, and `/gaps` HTTP smoke.
- Result: all final checks pass. One known Starlette TestClient deprecation warning remains. Early verification attempts failed once from running Alembic at the wrong working directory, once from curling before API readiness, and once because Docker had created root-owned `.next` artifacts; all were corrected and rerun successfully.

## Next Agent Notes

- Continue from: review the running workspace at `http://localhost:13000/gaps`, then add failed/no-result search signals to gap scoring.
- Watch out for: API runs on `18000` in the current environment; keep deep-research approval human-gated. The workspace contains an empty `.git` directory but is not a usable Git repository.
- Suggested next command: `make test && make lint && make build`.
