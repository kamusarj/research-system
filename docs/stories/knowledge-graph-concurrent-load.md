# US-KNOWLEDGE-GRAPH-CONCURRENT-LOAD Scale concurrent Knowledge Graph reads

## Status

implemented

## Lane

normal

## Product Contract

Knowledge Graph reads must stay responsive under concurrent access without changing canonical
graph data, authorization, write governance or the response schema. The browser must not refetch
unchanged graph projections unnecessarily. An explicit multi-user runtime mode must serve the API
with multiple worker processes, bounded PostgreSQL connection pools, compressed large JSON
responses and the production Next.js server instead of development reloaders.

## Relevant Product Docs

- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `Docs/Graph Intelligence v2 Operations Runbook.md`
- `README.md`

## Acceptance Criteria

- Initial Hierarchy uses only the hierarchy and semantic-overlay graph reads; it does not recompute
  the full projection through `/graph/stats`.
- Graph and neighbor queries are deduplicated in the browser, remain fresh for 30 seconds, stay in
  memory for five minutes and do not refetch solely because the window regains focus.
- Large graph JSON responses support gzip and carry private, bounded browser-cache headers.
- The default developer runtime retains reload behavior, while the opt-in multi-user Compose overlay
  runs four configurable Uvicorn workers and a production Next.js server.
- PostgreSQL pool size, overflow, timeout and recycle limits are explicit and validated; SQLite test
  behavior remains unchanged.
- A concurrent runtime check completes without failed requests and records latency/throughput proof.
- No graph response field, canonical data, mutation path, auth rule or governance behavior changes.

## Design Notes

- Client cache is per browser and never shared between identities.
- HTTP graph caching is `private`; an intermediary must not reuse authenticated graph responses
  across users.
- Multi-process workers balance CPU/request load inside one API container. Horizontal multi-host
  scaling still requires an external load balancer and a shared rate limiter.
- The process-local limiter remains suitable only for trusted local operation; shared deployments
  must follow the existing auth/TLS/gateway warning in the operations runbook.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | DB engine options and graph browser-query cache policy. |
| Integration | Graph cache/compression headers and unchanged response contract. |
| E2E | Existing responsive Knowledge Graph workflow remains green. |
| Platform | Rendered Compose modes and concurrent live request benchmark. |
| Release | Ruff, focused API/frontend tests, ESLint, Compose config and live readiness. |

## Harness Delta

Intake #75 records the performance maintenance request. No schema or architecture source-of-truth
decision changes; the multi-user mode is an opt-in deployment overlay.

## Evidence

- Baseline single-process development API, 60 relationship-graph requests at concurrency 20:
  60/60 HTTP 200, average `457.53 ms`, maximum `771.61 ms`; uncompressed response size `297,275`
  bytes.
- Final four-worker runtime, same 60 requests at concurrency 20:
  - direct uncompressed: 60/60 HTTP 200, average `144.46 ms`, maximum `218.14 ms`;
  - direct gzip: 60/60 HTTP 200, average `122.85 ms`, maximum `245.99 ms`;
  - production frontend proxy + gzip: 60/60 HTTP 200, average `130.13 ms`, maximum `254.16 ms`.
- Gzip reduces the real 429-node relationship response from `297,275` to `28,443` bytes
  (approximately 90.4%).
- Browser E2E proves initial Hierarchy performs exactly two graph projection reads, zero
  `/graph/stats` reads, and switching to Network reuses the relationship projection without a new
  request.
- Full API Ruff and 323/323 tests pass. Full frontend ESLint, TypeScript, 32 Vitest files / 143
  tests and the 15-route production build pass. Responsive graph Playwright passes 3/3.
- Compose profile, startup healthchecks, installed systemd launcher, readiness and an idempotent
  second service restart pass; the Smart Exam container IDs remain unchanged.
- Harness verification/completion passed. Standard trace #77 records intake #75 and its proof.
