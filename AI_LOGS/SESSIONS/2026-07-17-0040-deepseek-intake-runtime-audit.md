# Session Log

## Context

- User request: Recheck whether source intake and processing fully work, reproduce the reported DeepSeek API failure, and test until errors are eliminated.
- Agent: Codex.
- Date/time: 2026-07-17 00:40 +07.

## Work Done

- Files changed: `apps/api/app/api/ingestion.py`, `apps/api/app/api/search.py`, `apps/api/app/schemas/ingestion.py`, `apps/api/app/services/ingestion.py`, `apps/api/app/services/sources/errors.py`, `apps/api/app/services/sources/paper.py`, four backend test files, `apps/web/e2e/research-workspace.spec.ts`, `README.md`, `Docs/Research System Completion Plan.md`, handoff/task/decision logs, and this session log.
- Behavior changed: Added registry-neutral CSL fallback for valid non-Crossref DOIs; replaced PostgreSQL-incompatible full-row `DISTINCT` search with relationship `EXISTS`; validated retry provider overrides; replaced removed legacy retry providers with the configured default; and stopped logging expected typed source/provider failures as crash tracebacks.
- Commands/tests run: Inspected provider/runtime/job state; queried the official DeepSeek `/models` endpoint; ran minimal and full-schema DeepSeek probes; submitted and polled live GitHub/article/arXiv/PDF/Facebook/private URL jobs; approved one DeepSeek item and checked research/search/graph; ran Ruff, full/focused backend suites, frontend lint/type/Vitest/build, Compose validation, 12 Playwright browser tests, final Docker rebuild/recreate, all-route HTTP smoke checks, no-active-job assertions and a fresh log audit.

## Decisions Made

- Decision: Preserve `deepseek-v4-pro`; the official live `/models` result proves it is valid for the configured account, and both JSON-mode probes succeeded.
- Decision: Treat Facebook transcript absence and private URL rejection as explicit expected outcomes rather than attempting access-control bypasses.
- Decision: Use DOI content negotiation only after Crossref 404, retaining Crossref as the normal first lookup and all existing SSRF/size/redirect protections.
- Decision: Require a real PostgreSQL search smoke after approval because SQLite cannot expose PostgreSQL JSON equality failures.

## Verification

- Tests/checks: Ruff; 43 backend tests; frontend ESLint, TypeScript, 12 Vitest tests, Next.js production build; 12 Playwright tests across desktop/tablet/mobile; Compose config; Markdown fences; DeepSeek `/models` and full-schema probe; live source matrix; approval/search/graph; all primary routes; service health/state; fresh log scan.
- Result: All checks pass. DeepSeek GitHub/article/paper/PDF jobs completed in one attempt with `deepseek-v4-pro`; Facebook returned expected `partial_success`; private URL returned `INVALID_URL`; the next valid worker job completed; DOI fallback succeeded and deduplicated; approved research is searchable and graph-visible; no active jobs remain; fresh rebuilt-runtime logs contain no 500, traceback or exception.

## Known Issues

- Facebook Reels can still provide public metadata without a lawful public transcript; this remains a visible `TRANSCRIPT_UNAVAILABLE` partial result.
- Scanned PDFs still require the planned OCR adapter, and JS-only/paywalled/private sources keep their documented partial/failure boundaries.
- The host `apps/api/.venv` still has stale pre-monorepo paths; backend tests pass in an ephemeral Compose container.
- The upstream Starlette/httpx TestClient deprecation warning remains; it does not affect the 43 passing tests.

## Next Best Action

- Obtain product-owner acceptance on the verified DeepSeek intake path, then return to the planned intake receipt/attachment-storage specification before Discord work.
