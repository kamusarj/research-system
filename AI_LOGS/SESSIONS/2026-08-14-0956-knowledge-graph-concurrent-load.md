# Knowledge Graph concurrent-load hardening

## Context

- User request: keep Knowledge Graph responsive and load-balanced when many users access it.
- Agent: Codex
- Date/time: 2026-08-14 09:56 +07

## Work Done

- Files changed:
  - `.env.example`, `docker-compose.yml`, `docker-compose.multi-user.yml`
  - `apps/api/app/core/config.py`, `apps/api/app/db.py`, `apps/api/app/main.py`
  - `apps/api/app/api/graph.py`, `apps/api/tests/test_graph_concurrency.py`
  - `apps/web/app/graph/page.tsx`, `apps/web/hooks/use-knowledge-graph.ts`
  - `apps/web/hooks/use-knowledge-graph.test.tsx`
  - `apps/web/lib/knowledge-graph/graph-visualization.ts` and its test
  - `apps/web/e2e/graph-hierarchy.spec.ts`
  - `apps/web/components/document-ai-editor.test.tsx`
  - `scripts/start_local_autostart.sh`, `scripts/verify_local_autostart.sh`
  - `scripts/verify_graph_multi_user.sh`
  - `README.md`, the graph plan/runbook, story and AI handoff logs
- Behavior changed:
  - Removed the redundant full `/graph/stats` projection from the Graph page and derives component
    and type metrics from the already loaded relationship projection.
  - React Query keeps graph data fresh for 30 seconds, cached for five minutes, does not refetch on
    window focus and deduplicates repeated neighbor expansion.
  - Graph reads use private bounded browser-cache headers; FastAPI compresses responses over 1 KiB.
  - PostgreSQL engine pools are explicit, bounded and pre-ping/recycle stale connections.
  - Added multi-user Compose mode with four configurable Uvicorn workers and standalone production
    Next.js. Workstation autostart now uses this mode and waits for API/frontend healthchecks.
  - Added the missing `summary` value to an existing Document test fixture so full TypeScript and
    production build can run.
- Commands run:
  - Required Harness bootstrap, intake #75 and story lifecycle commands.
  - Full API Ruff and pytest.
  - Full frontend ESLint, TypeScript, Vitest and Next production build.
  - Responsive graph Playwright on desktop/tablet/mobile.
  - Compose/profile/autostart verification and two systemd service restarts.
  - Live 60-request benchmarks at concurrency 20 through the API and frontend proxy.

## Reasoning / Decisions

- Decision: remove redundant graph work before adding capacity.
- Reason: scaling repeated full projections wastes every worker and database connection.
- Decision: use bounded private browser caching, not a shared proxy cache.
- Reason: it reduces repeat reads without risking reuse of an authenticated response across users.
- Decision: use four Uvicorn processes in one container with explicit pool budgets.
- Reason: this provides real process-level connection distribution on the current single host while
  preserving the existing Compose topology and canonical PostgreSQL source.
- Decision: retain development reload mode in base Compose and put production serving in an
  explicit overlay used by autostart.
- Alternative considered: horizontal replicas plus Redis/gateway. This remains the next scale tier
  because shared rate limiting, invalidation, TLS and multi-host health routing require deployment
  infrastructure not authorized or configured in this local-first request.

## Verification

- Baseline: single-process development API, 60 requests at concurrency 20, 60/60 HTTP 200,
  `457.53 ms` average / `771.61 ms` maximum.
- Final four-worker API:
  - uncompressed direct: `144.46 ms` average / `218.14 ms` maximum;
  - gzip direct: `122.85 ms` average / `245.99 ms` maximum;
  - gzip through production frontend proxy: `130.13 ms` average / `254.16 ms` maximum;
  - all three runs completed 60/60 with zero failures.
- Payload: `297,275` bytes uncompressed to `28,443` bytes gzip, approximately 90.4% smaller.
- API: Ruff passed; 323/323 pytest passed.
- Frontend: ESLint and TypeScript passed; 32 files / 143 Vitest tests passed; 15-route production
  build passed.
- Playwright: graph desktop/tablet/mobile passed 3/3 and proves exactly two initial graph reads,
  zero `/graph/stats` request and cache reuse when switching to Network.
- Platform: four worker processes observed; API/frontend healthy; readiness graph valid; static
  assets HTTP 200; no recent API/frontend error signature.
- Autostart: installed launcher uses the overlay, waits for health, and an idempotent second restart
  preserved all Business AI Agents and Smart Exam container IDs.
- Harness: story verification/completion passed; standard trace #77 meets the normal-lane tier.
- Known test iterations corrected: duplicate `Accept-Encoding` in `Vary`; an E2E request-count
  assertion that ran before the canvas loaded; and startup verification that raced the first
  config-materializing API recreation.

## Next Agent Notes

- Continue from: live frontend `http://localhost:13000/graph`, API `http://localhost:18000`, four
  Uvicorn workers and standalone Next.js production server.
- Watch out for: `AUTH_MODE=disabled` is trusted-local only. Do not expose this host publicly or to
  untrusted users. Four process-local limiters are not a global quota.
- Next scale tier: enable auth/TLS, put a health-aware gateway in front, and use Redis for shared
  rate limiting/cache invalidation before horizontal multi-host replicas.
- Suggested check: `scripts/verify_graph_multi_user.sh && scripts/verify_local_autostart.sh`.
