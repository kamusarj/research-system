# Research System Runtime Restart

## Context

- User request: start the project.
- Agent: Codex `/root`.
- Date/time: 2026-07-25 12:06 +0700.

## Work Done

- Read the current handoff, task board, decisions and Graph Intelligence v2 operations runbook.
- Validated the base Compose configuration and inspected stopped Research System containers before
  making any runtime change.
- Restarted only `database`, `api`, `worker` and `frontend` with API port `18000`, frontend port
  `13000` and local CORS pointing to the frontend.
- Reused existing images and preserved the PostgreSQL and document-object volumes.
- Files changed: `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, and this session log.

## Decisions Made

- Used the documented non-conflicting ports because Smart Exam owns host port `8000`.
- Did not rebuild images because the current request was only to run the existing project and the
  stopped containers/images were already present.
- Did not run a billable DeepSeek/OpenAI provider preflight; project health and graph readiness do
  not require an external model call.
- Left all `smart_exam_*` containers and the optional Ollama bridge untouched.

## Commands/Tests Run

- `docker compose config -q`
- `API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 docker compose up -d database api worker frontend`
- Direct API health, feature-discovery and readiness requests on port `18000`.
- Frontend root and proxied API health requests on port `13000`.
- `docker compose exec -T api alembic current`
- `docker compose exec -T api python -m app.operations verify-graph`
- `docker compose ps` and a five-minute API/worker/frontend startup-log error scan.

## Verification Result

- All four Research System services are up; PostgreSQL is healthy.
- Direct API health and proxied health return `{"status":"ok"}`; frontend root returns HTTP 200.
- Graph Intelligence v2, document workspaces, graph chat and rate limits report enabled.
- Readiness is `ready`; the graph is valid with 45 nodes, 32 edges, zero alias errors and no
  invariant violations.
- PostgreSQL migration is `a8b4c6d2e913 (head)`.
- Fresh startup logs contain no traceback, exception, fatal or HTTP 500 entry.
- All unrelated Smart Exam containers remained running and untouched.

## Known Issues

- Real Graph v2 chat acceptance still depends on restoring TCP/443 reachability to
  `api.deepseek.com` and completing the product-owner walkthrough.
- Host port `8000` remains owned by Smart Exam, so this project must continue using API `18000`.

## Next Best Action

- Open `http://localhost:13000` and continue product testing. When DeepSeek network access is
  restored, run the secret-safe `verify-chat-provider` preflight before the final live chat
  acceptance walkthrough.
