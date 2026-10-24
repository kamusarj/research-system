# Session Log

## Context

- User request: Start the project.
- Agent: Codex
- Date/time: 2026-08-02 18:20 +07

## Work Done

- Files changed:
  - `AI_LOGS/HANDOFF.md`
  - `AI_LOGS/TASKS.md`
  - `AI_LOGS/SESSIONS/2026-08-02-1820-start-local-project.md`
- Behavior changed:
  - Restarted the existing PostgreSQL, API, worker and frontend containers.
  - No application code, image or persisted application data was changed.
- Commands run:
  - `docker compose config -q`
  - `docker compose ps --all`
  - `docker ps --format ...`
  - `API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 docker compose up -d --no-build database api worker frontend`
  - Direct API health/readiness, frontend root and proxied API health checks with `curl`
  - `docker compose exec -T api alembic current`
  - `docker compose exec -T api python -m app.operations verify-graph`
  - Fresh API/worker/frontend/database log scan for errors

## Reasoning / Decisions

- Decision: Reuse the existing images and preserved volumes with the documented host-port override.
- Reason: The current images already contain the latest verified application, while the unrelated
  `smart_exam_backend` owns host port `8000`; rebuilding or changing that other project was not
  required to start this stack.
- Alternatives considered: Rebuilding the images or stopping the unrelated service on port `8000`;
  neither was needed.

## Verification

- Tests/checks:
  - Compose configuration and service status
  - Direct API `/api/v1/health`
  - API `/api/v1/system/readiness`
  - Frontend `/`
  - Proxied frontend `/api/v1/health`
  - Alembic current revision
  - Canonical graph invariant verifier
  - Fresh startup log scan
- Result:
  - Database healthy; API, worker and frontend running
  - API and proxied health: `ok`
  - Frontend: HTTP 200
  - Readiness: `ready`
  - Migration: `f8b3d1e6a204 (head)`
  - Graph: valid, 45 nodes, 32 edges, no errors
  - No fresh error, exception, traceback, fatal or HTTP 500 log entry

## Known Issues

- Repository defaults still conflict with the unrelated service on host port `8000`; continue using
  API `18000`, frontend `13000` and CORS origin `http://localhost:13000` on this host.

## Next Agent Notes

- Continue from: Running local stack at frontend `http://localhost:13000` and API
  `http://localhost:18000`.
- Watch out for: Do not stop or modify the unrelated `smart_exam_*` containers.
- Suggested next command:
  `API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 docker compose ps`
