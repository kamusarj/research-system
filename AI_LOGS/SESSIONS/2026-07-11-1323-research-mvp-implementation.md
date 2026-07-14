# Session Log

## Context

- User request: triển khai trực tiếp toàn bộ Research System bám sát plan có sẵn, kiểm tra tuần tự từng task và báo cáo verification.
- Agent: Codex.
- Date/time: 2026-07-11 13:23 Asia/Bangkok.

## Work Done

- Files changed:
  - Tạo backend FastAPI, SQLAlchemy models, Alembic migrations, services, routers, schemas, seed và tests dưới `backend/`.
  - Tạo frontend Next.js App Router, React Query provider, Research/Search/Graph/Collector/Training screens và shared components dưới `frontend/`.
  - Tạo `docker-compose.yml`, `.env.example`, `.gitignore`, `Makefile`, `README.md` và Docker build files.
  - Tạo `Docs/Research System MVP Specification.md`.
  - Cập nhật `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, `AI_LOGS/DECISIONS.md`.
- Behavior changed:
  - Repo docs-only trở thành MVP chạy được với research lifecycle, search, graph, AI enrichment, RSS collection và governed training export.
  - API chuẩn hóa dưới `/api/v1`; PostgreSQL migrations chạy tự động trong Docker.
- Commands run:
  - `ruff format/check`, `python -m compileall`, `pytest --cov`.
  - `alembic revision --autogenerate`, `alembic upgrade head`, `python -m app.seed` hai lần.
  - `npm install`, `npm audit --omit=dev`, `npm run lint`, `npm run typecheck`, `npm run build`.
  - `docker compose config -q`, `docker compose up -d --build`, curl health/frontend/research endpoints, container logs.
  - Markdown fence validation.

## Reasoning / Decisions

- Decision: use `Docs/Research System Implementation Plan.md` because root `PLAN.md` does not exist and handoff names this as the canonical plan.
- Decision: use database-backed lightweight search/graph projections for MVP.
- Reason: explicitly allowed by plan, minimal operational footprint, stable API upgrade path.
- Decision: use deterministic mock AI by default and optional Ollama adapter.
- Decision: keep RSS synchronous/manual in MVP and persist source/run/evaluation/provenance.
- Decision: apply a PostCSS patch override instead of the breaking `npm audit fix --force` suggestion.

## Verification

- Backend tests: 7 passed, coverage 87%.
- Backend checks: Ruff, syntax/import, SQLite and PostgreSQL migrations pass.
- Frontend: lint/typecheck/build pass; 8 routes built.
- Dependency audit: 0 vulnerabilities after PostCSS patch override.
- Docker smoke: database healthy, API health HTTP 200, research HTTP 200, frontend HTTP 200.
- Result: MVP acceptance paths implemented and verified.

## Known Issues

- Default port 8000 is occupied by an unrelated container; smoke instance uses API 18000 and frontend 13000.
- FastAPI/Starlette TestClient emits a non-failing `httpx` deprecation warning.
- Production-only components intentionally deferred by plan are not part of this session.

## Next Agent Notes

- Continue from: user review of the running MVP at `http://localhost:13000`.
- Watch out for: do not stop `smart_exam_*` containers; do not replace PostgreSQL truth with a projection store.
- Suggested next command: `API_PORT=18000 FRONTEND_PORT=13000 NEXT_PUBLIC_API_URL=http://localhost:18000/api/v1 docker compose ps`.
