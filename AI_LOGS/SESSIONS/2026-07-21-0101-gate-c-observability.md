# Gate C Production Observability

## Context

- User request: continue the active completion goal after reading the AI logs, completing accepted
  project work in order while the OpenAI/product-owner acceptance blocker remains external.
- Agent: Codex.
- Date/time: 2026-07-21 01:01 +07.

## Work Done

- Files changed:
  - `apps/api/app/core/observability.py`
  - `apps/api/app/core/config.py`, `apps/api/app/core/runtime_controls.py`, `apps/api/app/main.py`
  - `apps/api/app/worker.py`
  - `apps/api/app/services/ingestion.py`
  - `apps/api/app/services/document_processing.py`
  - `apps/api/app/services/graph_chat.py`
  - `apps/api/tests/test_observability.py`
  - `apps/api/pyproject.toml`, `apps/api/uv.lock`
  - `.env.example`, `docker-compose.yml`, `README.md`
  - `Docs/Graph Intelligence v2 Operations Runbook.md`
  - `Docs/Research System Completion Plan.md`
  - `docs/stories/gate-c-observability/{overview,design,execplan,validation}.md`
  - `docs/decisions/0009-production-observability.md`
  - `AI_LOGS/DECISIONS.md`, `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`
  - this session log.
- Added validated/generated request correlation and `X-Request-ID` response headers.
- Added strict JSON stdout formatting for application API/worker logs and suppressed default
  `httpx`/`httpcore` INFO plus Uvicorn raw access logs.
- Added process-local bounded-label HTTP, provider, token, rate-limit and worker-job metrics.
- Added a secure-default `/metrics` contract: disabled 404, enabled-without-secret 503, incorrect or
  missing bearer 401, correct bearer Prometheus exposition. The route is absent from OpenAPI.
- Preserved PostgreSQL `AuditEvent` as the authoritative business audit trail.
- Added deployment configuration and operating guidance without storing any real credential.
- Harness recorded intake #6, high-risk story `US-GATEC-OBSERVABILITY`, decision 0009 and completed
  the story with all proof flags. Detailed trace #7 meets the high-risk 3/3 tier; audit entropy is
  `5/100` only because `US-GV2-ACCEPT` remains intentionally unverified. Harness backlog #2 captures
  ambiguous `--verify` CLI help.

## Decisions Made

- Operational logs use an allowlist rather than arbitrary `LogRecord` serialization; bodies,
  headers, raw URLs/query strings, document/chat content, provider output and exception messages are
  not telemetry fields.
- Metrics use route templates and typed outcomes rather than UUIDs or content labels.
- Metrics remain disabled by default and require a dedicated bearer secret when enabled.
- The API exposes process-local metrics; the worker emits structured job telemetry but does not open
  an unauthenticated scrape listener. Cross-process aggregation is deferred to deployment design.
- External deployment owns TLS/network policy, secret injection/rotation, scrape retention,
  dashboards, alerts and multi-replica aggregation.

## Commands / Tests Run

- `scripts/bootstrap-harness.sh` and focused Harness matrix/context queries.
- Harness intake/story/decision/update/complete/query commands.
- `uv lock`, `uv sync --all-extras`.
- `uv run ruff check app tests`.
- `uv run python -m pytest -q` and the Harness completion rerun.
- `docker compose config --quiet`.
- `docker compose build api worker`.
- Temporary enabled Compose API runtime; unauthorized and authorized `/metrics` probes; request-ID,
  readiness, metric-label and JSON-log inspection; secure-default restore.
- `E2E_BASE_URL=http://127.0.0.1:13000 npm run test:e2e`.
- Final health, disabled metrics and graph-readiness probes.

## Verification Result

- Ruff passes.
- 104 backend tests pass with the known upstream Starlette/TestClient deprecation warning.
- 27/27 Playwright cases pass across desktop, tablet and mobile in the authoritative final run.
- Compose configuration and final API/worker image builds pass with `prometheus-client==0.25.0`.
- Enabled runtime returned 401 without the test bearer and valid Prometheus text with it. Labels used
  route templates and omitted concrete IDs/query markers. JSON runtime logs correlated
  `runtime-proof-21` without a raw URL or request content.
- Runtime was restored to `METRICS_ENABLED=false`: health 200, `/metrics` 404, readiness `ready`, 45
  canonical nodes, 32 edges and zero invariant errors. Unrelated `smart_exam_*` services were not
  touched.
- Two non-authoritative Playwright attempts failed for explained environment reasons: the first used
  default port 3000 instead of runtime port 13000; the second overlapped source reload with an old API
  image missing the new dependency. Recreating from the built image produced the clean 27/27 run.

## Known Issues

- The current OpenAI credential is still rejected; real graph chat and final product-owner acceptance
  remain external blockers and were not self-marked complete.
- Auth/RBAC and managed secret deployment remain the next Gate C design/implementation slice.
- Production MinIO operations/migration, OCR/browser rendering and projection upgrades remain open.
- Metrics are per API process and reset on restart; production aggregation, retention, alerting and
  dashboards are not bundled.
- `apps/api/.venv/bin/pytest` has a stale shebang; `uv run python -m pytest` is the verified command.
- The first story trace (#6) lacked Harness's required high-risk token estimate and scored 2/3; the
  immutable replacement trace #7 includes the estimate/explanation and meets detailed 3/3.

## Next Best Action

- Replace/verify the OpenAI secret outside source control if available; otherwise define and
  implement the production identity/session/RBAC and managed-secret contract before non-local
  exposure.
