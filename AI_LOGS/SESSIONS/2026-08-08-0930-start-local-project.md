# Session: Start local project (2026-08-08 09:30)

## User request

- Run the project (chạy project cho tôi).

## Files changed

- None (no application code, image or data change).

## Decisions made

- Used the documented port override `API_PORT=18000 FRONTEND_PORT=13000
  API_CORS_ORIGINS=http://localhost:13000` because the unrelated
  `smart_exam_backend` container owns host port 8000 (blocked task entry in
  `AI_LOGS/TASKS.md`).

## Commands/tests run

- `API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000
  docker compose up -d database api worker frontend`
- `docker compose ps` (same override)
- `curl -s -o /dev/null -w "%{http_code}" http://localhost:13000/`
- `curl -s http://localhost:18000/api/v1/health`
- `curl -s http://localhost:13000/api/v1/health` (frontend proxy)

## Verification result

- All four core services running: database (healthy), api, worker, frontend.
- Frontend `/` returns HTTP 200.
- Direct API health `{"status":"ok"}`; proxied health through frontend also
  `{"status":"ok"}`.

## Known issues

- None new. Port 8000 remains owned by the unrelated `smart_exam_backend`;
  keep using the 18000/13000 override.

## Next best action

- Stack is ready at `http://localhost:13000` (UI) and `http://localhost:18000`
  (API `/docs`). No further action required unless the user asks for a rebuild
  or a specific feature check.
