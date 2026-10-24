# Session Log

## Context

- User request: Run the project locally.
- Agent: Codex.
- Date/time: 2026-07-17 09:39 +07.

## Work Done

- Files changed: `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, and this session log.
- Behavior changed: Started the existing Research System Docker Compose services; no application code, database content, or configuration file was changed.
- Commands run: inspected the required handoff/task/decision files and relevant run documentation; checked Docker port ownership; ran `API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 docker compose up -d`; checked direct/proxied health, frontend HTTP status, Compose service state, and recent logs.

## Reasoning / Decisions

- Decision: Use ports `18000` for the API and `13000` for the frontend, matching the documented workaround.
- Reason: The unrelated `smart_exam_backend` container already owns host port `8000`.
- Alternatives considered: The default Compose ports were rejected because they would conflict; rebuilding images was unnecessary because the current project images already existed and the request was only to run the project.

## Verification

- Tests/checks: Direct `GET http://localhost:18000/api/v1/health`, frontend `GET http://localhost:13000/`, proxied `GET http://localhost:13000/api/v1/health`, `docker compose ps`, and a fresh API/worker/frontend error-log scan.
- Result: All HTTP checks returned 200; direct and proxied health returned `{"status":"ok"}`; PostgreSQL is healthy; all four core services are up; no fresh error, exception, traceback, fatal, or HTTP 500 log entries were found.

## Known Issues

- Host port `8000` remains occupied by the unrelated Smart Exam backend, so this project must continue using the documented port override while that container is running.

## Next Agent Notes

- Continue from: The Research System is available at `http://localhost:13000`; API docs are at `http://localhost:18000/docs`.
- Watch out for: Do not stop or modify the `smart_exam_*` containers; do not expose provider secrets in logs.
- Suggested next command: `docker compose ps`.
