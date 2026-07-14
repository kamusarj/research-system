# Session Log

## Context

- User request: rebuild the Docker stack after the Research Intelligence refactor.
- Agent: Codex.
- Date/time: 2026-07-14 00:05 Asia/Saigon.

## Work Done

- Files changed: `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, and this session log only.
- Behavior changed: rebuilt API, worker and frontend images; recreated the project containers while preserving the PostgreSQL volume.
- Commands run:
  - `docker compose up -d --build`
  - `docker compose up -d` with `API_PORT=18000`, `FRONTEND_PORT=13000`, matching CORS and public API URL overrides.
  - HTTP health, graph and primary-route smoke checks.
  - `docker compose ps` and recent error-log inspection.

## Decisions Made

- Kept the known 18000/13000 host-port workaround because unrelated infrastructure still owns port 8000.
- Did not stop or alter any container outside this Compose project.

## Verification Result

- API, worker and frontend images built successfully; npm install inside the frontend image reported zero vulnerabilities.
- Database remained healthy and its existing volume was preserved.
- API health returned `ok` on port 18000.
- Graph API returned 8 nodes, 4 edges, no truncation and the PostgreSQL provider.
- `/`, `/ingestion`, `/research`, `/search`, `/graph`, `/gaps`, `/collector`, and `/training` all returned HTTP 200 on port 13000.
- API, worker and frontend recent logs contained no error, traceback or compile-failure matches.

## Known Issues

- The first recreate attempt could not bind host port 8000 due to the already-documented unrelated container. The retry with documented overrides succeeded.

## Next Best Action

- Open <http://localhost:13000> and perform the pending visual EN/VI workflow review when an in-app browser session is available.
