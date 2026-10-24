# Start Local Project

## Context

- User request: Run the project.
- Agent: Codex.
- Date/time: 2026-08-09 22:10 +0700.

## Work Done

- Files changed: `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, and this session log.
- Behavior changed: restarted the existing `database`, `api`, `worker`, and `frontend` Compose
  services without rebuilding images or changing application code/data.
- Commands run:
  - Checked whether host ports `18000` and `13000` were available.
  - `API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 docker compose up -d database api worker frontend`
  - Direct API health and readiness requests on port `18000`.
  - Frontend root and proxied health requests on port `13000`.
  - `docker compose exec -T api alembic current`
  - `docker compose exec -T api python -m app.operations verify-graph`
  - `docker compose ps` and a bounded fresh-log error scan.

## Reasoning / Decisions

- Decision: preserve the existing images and Docker volumes and use the documented host-port
  override.
- Reason: the requested outcome was to run the current project; the accepted local operations use
  API `18000` and frontend `13000` because the default API port `8000` belongs to another project.
- Alternatives considered: rebuilding images was unnecessary because the current images started
  cleanly and passed all operational checks.

## Verification

- Tests/checks: container status, direct/proxied health, frontend HTTP response, readiness,
  migration head, graph invariant verification, and fresh API/worker/frontend log scan.
- Result: all four services are running; PostgreSQL is healthy; direct and proxied health are
  `ok`; frontend returns HTTP 200; readiness is `ready`; migration is `2d4e6f8a0b13 (head)`; graph
  is valid with 45 nodes and 32 edges; no startup error signature was found.

## Known Issues

- No new project issue found. Default port `8000` remains unavailable; keep using the documented
  `18000`/`13000` override.

## Next Agent Notes

- Continue from: frontend `http://localhost:13000`; API docs `http://localhost:18000/docs`.
- Watch out for: host port `8000` remains occupied by the unrelated Smart Exam project.
- Suggested next command: `docker compose ps`.
