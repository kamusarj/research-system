# Session Log

## Context

- User request: Refactor dự án theo một kiến trúc chung, không để application code lẫn lộn ở root.
- Agent: Codex.
- Date/time: 2026-07-12 23:53 +07.

## Work Done

- Files changed: moved `backend/` to `apps/api/` and `frontend/` to `apps/web/`; updated `Makefile`, `docker-compose.yml`, `README.md`, `Docs/Research System Architecture Design.md`, `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, and `AI_LOGS/DECISIONS.md`; added `apps/README.md` and this session log.
- Behavior changed: repository paths now follow a deployable-app monorepo convention. Stable root commands and `/api/v1` behavior are unchanged.
- Commands run: repository/docs inspection, path reference search, `docker compose config -q`, `make test`, `make lint`, `make build`, and `docker compose build api frontend`.

## Reasoning / Decisions

- Decision: use `apps/api` and `apps/web`, while retaining `Docs/`, `AI_LOGS/`, and operational entrypoints at root.
- Reason: this gives current and future deployables one clear home without disrupting Compose/Make usage or repository agent conventions.
- Alternatives considered: moving all infrastructure into another directory was deferred because Compose is the single local runtime entrypoint; adding `packages/` now was rejected because no cross-app shared code exists.

## Verification

- Tests/checks: 7 backend tests, Ruff, ESLint, Next.js production build, Compose config validation, API Docker image build, and frontend Docker image build.
- Result: all pass. Pytest retains one known FastAPI/Starlette TestClient deprecation warning; no functional failure.

## Next Agent Notes

- Continue from: use `apps/api` and `apps/web` for all application work.
- Watch out for: historical session logs intentionally retain the old paths because they describe past state; default host port 8000 is still occupied by an unrelated project.
- Suggested next command: `docker compose up --build` or the documented port-override command for the next smoke review.
