# Session Log

## Context

- User request: start the project.
- Agent: Codex.
- Date/time: 2026-07-13 22:50 +07.

## Work Done

- Files changed: AI handoff and this session log only.
- Runtime changed: started Docker Desktop and launched the project with Docker Compose at frontend port 13000 and API port 18000, preserving the unrelated service on port 8000.
- Commands run: Docker engine readiness check, `docker compose up --build -d`, seed command, Compose status/log inspection, API health and primary-route HTTP smoke checks.

## Decisions Made

- Used the documented port override because host port 8000 belongs to the unrelated `smart_exam_backend` project.
- Seeded the fresh PostgreSQL volume so the UI has demo research data.

## Verification Result

- `database` is healthy; `api`, `worker`, and `frontend` are running.
- PostgreSQL migration `4a6e8b2c9d10` applied successfully.
- API health and `/`, `/ingestion`, `/graph`, `/research`, `/search`, `/collector`, `/gaps`, and `/training` all return HTTP 200.
- Worker log reports `Intake worker started`; API reports successful startup.

## Known Issues

- In-app browser is unavailable, so this session verifies HTTP behavior but not visual layout.
- Existing Starlette/httpx test deprecation warning is unchanged.

## Next Best Action

- Open `http://localhost:13000`, visually review bilingual intake/graph workflows, then continue with PDF and GitHub-specific extractors.
