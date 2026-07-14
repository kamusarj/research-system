# AI Handoff Log

## Current Goal

- Immediate priority: stop feature work and reproduce/fix the multiple errors reported by the user after the Docker rebuild. Current state is not accepted as stable.
- Latest session goal: stabilize and extend the existing Research Intelligence System around source adapters, review workflow and a real bounded knowledge graph UI.

- Goal hiện tại: hoàn thiện Research System core cho URL-to-knowledge trước khi xây Discord bot.
- Người yêu cầu: Linh.
- Trạng thái: implementing; completion Gates A-B complete, Gate C in progress.

## Current State

- IMPORTANT: the user reports that the rebuilt application still has many errors. Previous HTTP 200 checks and absence of obvious container log errors are insufficient; the implementation must be treated as needing debugging until the actual UI flows are reproduced and verified.
- Docker images were rebuilt on 2026-07-14 and the database/api/worker/frontend stack was recreated successfully on ports 18000/13000 with the existing PostgreSQL volume preserved.
- Graph API now returns a validated `{nodes, edges, meta}` contract with default/hard limits, filters, search, 1-2 hop traversal and neighbor expansion. `GRAPH_DATA_PROVIDER=postgres` is the default; `mock` is contract-valid and `neo4j` fails explicitly until its adapter is implemented.
- URL intake now dispatches through normalized GitHub, article, Facebook Reel and PDF adapters. GitHub/article extraction is implemented; Reel stops at `needs-transcript`; PDF stops at `needs-text-layer` without default OCR.
- The graph UI is split into API/hooks/mapper/theme/layout/canvas/toolbar/filter/legend/details/evidence modules. Cytoscape is created once, preserves positions, resizes via `ResizeObserver`, and cleans up listeners/instance on unmount.
- Research uses the existing lifecycle: `approved` is the published/searchable/graph-visible state. The UI now has all/review/published/rejected tabs, and rejected research can be resubmitted.

- AI provider registry now includes Mistral (`mistral-large-latest` by default) through strict JSON Schema chat completions; configure it with `MISTRAL_API_KEY` and optional `MISTRAL_MODEL`.
- URL intake is asynchronous: API submissions enter a durable PostgreSQL queue and the Compose `worker` processes them with leases, exponential retry and dead-letter/manual retry.
- Latest migration is `4a6e8b2c9d10`; API submit now returns HTTP 202 for newly queued links and HTTP 200 for an existing URL.
- FastAPI nằm tại `apps/api/`, Next.js nằm tại `apps/web/`; mọi deployable app mới tiếp tục đặt dưới `apps/`.
- Root chỉ giữ tài liệu/quy ước toàn repo và các entrypoint vận hành như `README.md`, `Makefile`, `docker-compose.yml`.
- PostgreSQL là database trong Docker; SQLite được dùng cho local test nhanh.
- Migrations: `22b42804e1f5`, `b4519e47487f`, `5d7a8c91e2f0` và `9f3c2a7b1d44`.
- App chạy bằng `docker compose up --build` hoặc các lệnh trong `README.md`.
- Test chạy bằng `make test`; lint bằng `make lint`; frontend build bằng `make build`.
- Docker smoke instance hiện đang chạy ở frontend `http://localhost:13000` và API `http://localhost:18000` vì port 8000 đang bị project khác chiếm.
- Gap workspace nằm tại `/gaps`; API detector/workflow nằm dưới `/api/v1/gaps`, với compatibility read endpoint `/api/v1/graph/gaps`.
- Completion plan nằm tại `Docs/Research System Completion Plan.md`; link intake UI ở `/ingestion`, API ở `/api/v1/ingestion/links`.
- AI registry hỗ trợ mock, Ollama, OpenAI, DeepSeek, Gemini và OpenRouter; chỉ mock/Ollama usable khi chưa cấu hình API key.

## Completed

- [x] Typed graph node/edge/meta schemas with duplicate, dangling-edge, self-loop and metadata count validation.
- [x] Bounded graph query/filter/search/neighbors endpoints and deterministic stable projection IDs.
- [x] Source adapter registry with URL detection/canonicalization and normalized source schema.
- [x] Practical GitHub and Article adapters; safe Facebook Reel/PDF pending states.
- [x] Refactored responsive Cytoscape workspace with loading/empty/error/retry/truncation states, filters, selection, details, evidence, hide/expand, fit/reset/re-layout.
- [x] Research review tabs and reject/resubmit API/UI workflow.
- [x] Dashboard gap wording and system flow corrected; graph/source environment and README documentation updated.
- [x] Frontend Vitest/Testing Library foundation and graph lifecycle/state/dedup tests.

- [x] Fixed intake resubmission: failed/dead-letter URLs now requeue with the newly selected provider instead of silently returning the stale submission; UI shows queued/existing feedback.
- [x] Mistral provider adapter, strict structured output validation, environment/Compose wiring, registry/UI discovery and request-shape tests.
- [x] Gate C worker foundation: durable intake queue, separate worker service, retry/backoff, lease recovery, dead-letter state, manual retry and polling UI.
- [x] Phase 0 MVP specification và acceptance criteria.
- [x] Phase 1 FastAPI/Next.js/PostgreSQL/Docker foundation, migration, CORS, health và error format.
- [x] Phase 2 Research CRUD, lifecycle, versioning, comments, tags, relations, attachment metadata và UI editor/library.
- [x] Phase 3 approved-only search, filters, suggestions, related research và semantic API fallback.
- [x] Phase 4 rebuildable graph projection, node/ego/path/stats APIs và graph UI.
- [x] Phase 5 mock/Ollama AI adapter, provenance, embeddings, suggestion accept/reject UI.
- [x] Phase 6 RSS source/run/evaluation/dedup/review/auto-ingest workflow và UI.
- [x] Phase 7 Training Data Hub events/examples/governance/datasets/JSONL export và UI.
- [x] Seed data, backend tests, frontend lint/type/build, dependency audit và Docker smoke test.
- [x] Refactor repository thành monorepo `apps/api` + `apps/web`, cập nhật Compose/Make/README và tài liệu kiến trúc.
- [x] Phase 8 foundation: persisted low-coverage gaps, prioritize/assign/dismiss/snooze, deep-research draft, human approval gate và gap workspace UI.
- [x] Docker port override cho phép cấu hình CORS; frontend `.next` dùng named volume để không tạo root-owned build artifacts trên host.
- [x] Completion Gate A: source-neutral URL intake, safe public URL validation, extraction, content-hash dedup, structured classification, review/publish và provider registry.
- [x] Typed graph ontology projection, graph clusters/stats và Cytoscape.js interactive canvas.
- [x] Persistent EN/VI locale switcher cho toàn bộ application UI, gồm shell, dashboard, link intake, graph, research, search, collector, gaps và training workflows.

## In Progress

- [ ] Gate C: background jobs/retry, auth/RBAC, secret deployment, richer PDF/GitHub extraction, MinIO và observability.
- [ ] Neo4j/Meilisearch/pgvector adapters vẫn là projection upgrade; Discord adapter chỉ bắt đầu sau các completion gates.

## Next Best Actions

1. Reproduce the user-visible failures route by route, starting with `/graph`, `/ingestion`, `/research` and browser console/network errors. Do not add features before this audit.
2. Compare frontend API requests against the live `/api/v1` responses and inspect API/worker/frontend logs while triggering each failing action.
3. Fix the smallest confirmed causes, rerun tests/build, rebuild Docker, and perform real interaction checks before claiming stability.

## Decisions Locked

- PostgreSQL là source of truth; search và graph là projection rebuild được.
- API giữ prefix `/api/v1`.
- Mock AI là default; Ollama là optional adapter.
- AI không tự ghi đè human fields.
- Training example phải qua PII, policy và provenance checks.
- RSS là collector duy nhất trong MVP.
- Deployable application code nằm dưới `apps/`; chỉ tạo `packages/` khi có code thực sự dùng chung giữa nhiều app.
- Gap detector v1 dùng approved concept coverage và lưu projection có thể rebuild; deep-research report luôn bắt đầu ở draft và phải qua human review.
- Discord không chứa business logic; nó chỉ gọi source-neutral intake API với source metadata/idempotency key.
- Provider output luôn qua structured schema + Pydantic validation; API keys chỉ lấy từ environment và không trả qua API.

## Do Not Touch

- Không xóa/overwrite brainstorm, architecture và implementation plan.
- Không chạy `npm audit fix --force`; PostCSS đã được override lên bản vá an toàn mà không đổi Next.js.
- Không dừng các container `smart_exam_*`; chúng thuộc project khác.
- Không lưu secrets/PII trong repo hoặc AI logs.

## Known Issues

- User reports multiple errors after the latest rebuild; exact symptoms have not yet been captured. This is the highest-priority unresolved issue.
- HTTP status smoke checks passed, but they did not exercise client hydration, Cytoscape interactions, form mutations, review actions or browser console/network failures.
- In-app browser discovery returned no available browser sessions, so visual QA could not be completed. Component tests and HTTP route smoke passed.
- `GRAPH_DATA_PROVIDER=neo4j` is an explicit scaffold: it returns 503 when unconfigured and 501 when configured; no fake data or silent PostgreSQL fallback is used.
- PDF extraction currently stops at `needs-text-layer`; Facebook Reel stops at `needs-transcript`. Upload/transcript editing is follow-up work.

- The in-app browser remains unavailable, so visual UX review is still open. PostgreSQL migration, API/worker startup and HTTP route smoke now pass in Docker.
- Root `PLAN.md` không tồn tại; implementation dùng file kế hoạch được handoff xác nhận là `Docs/Research System Implementation Plan.md`.
- Pytest báo một deprecation warning từ FastAPI/Starlette TestClient về package `httpx`; không ảnh hưởng test result.
- Port mặc định API 8000 đang bị `smart_exam_backend` ngoài project chiếm trong máy hiện tại; Compose hỗ trợ `API_PORT`/`FRONTEND_PORT` override.
- Authentication/RBAC, MinIO binary upload, Meilisearch, Neo4j, Redis worker và production hardening là các hạng mục được plan defer sau MVP.
- Phase 8 chưa có failed-search/trend signal, weekly digest hoặc autonomous deep-research agent.
- Generic article extraction still does not support JS-heavy pages; PDF text-layer extraction and user-supplied Reel transcripts remain explicit follow-up work.
- Locale stores UI preference in browser local storage; research content and existing user-entered data remain in their original language by design.

## Verification

- Docker rebuild session: API/worker/frontend images built successfully; Compose startup initially hit the known external port-8000 conflict, then succeeded with documented 18000/13000 overrides. Health, graph API and all eight primary frontend routes pass; recent service logs contain no runtime errors.
- Current session: Ruff pass; 23 backend tests pass with the existing TestClient deprecation warning.
- Frontend: 5 Vitest tests pass; ESLint, TypeScript and Next.js production build pass; npm audit reports 0 vulnerabilities during install.
- Runtime: Docker database/api/worker/frontend are running on 18000/13000; health and all primary routes return HTTP 200.
- Live graph smoke: 8 unique nodes, 4 edges, zero dangling edges, valid meta/provider, and bounded neighbor response.
- `docker compose config -q` passes. Workspace still is not recognized as a Git repository despite a `.git` directory.

- Intake resubmission fix: Ruff pass; 16 tests pass; ESLint/build pass. Live `wailsapp/wails` resubmission changed OpenRouter dead-letter to DeepSeek queued, then reached `needs-review` after one worker attempt with structured classification.
- Mistral session: Ruff pass; 15 tests pass; Compose config pass; live provider registry returns Mistral without exposing keys; API and worker restart cleanly on ports 18000/13000.
- Current worker session: Ruff pass; 14 tests pass; SQLite migration upgrade/downgrade/upgrade pass; ESLint and Next.js production build pass; Compose config pass.
- Runtime smoke: Docker services `database`, `api`, `worker`, and `frontend` are running; PostgreSQL migration `4a6e8b2c9d10` applied; health and every primary frontend route return HTTP 200 on ports 18000/13000; seed contains one research item.
- Backend: Ruff pass; 12 tests pass. Link-intake migration upgrade/downgrade/upgrade pass trên SQLite và upgrade pass trên PostgreSQL.
- Frontend: ESLint/typecheck pass; Next.js production build pass (10 app routes plus not-found); npm audit reports 0 vulnerabilities.
- Docker: `docker compose config -q` pass; current smoke health API and every primary route (`/ingestion`, `/graph`, `/research`, `/search`, `/collector`, `/gaps`, `/training`) return HTTP 200 at ports 18000/13000.
- Markdown code fences và `docker compose config -q` pass.
- Git status không có vì workspace không phải Git repository.
