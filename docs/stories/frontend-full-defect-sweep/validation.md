# Validation

## Proof Strategy

Use a layered ladder: static checks and unit tests first, production compilation next, then the existing full Playwright suite and an independent live route audit that records route status, console/page errors, failed same-origin API responses, untranslated keys and horizontal overflow at three viewports.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Full Vitest suite plus focused regression tests for every corrected defect. |
| Integration | TypeScript validates client/API contract use; Next.js production build validates route compilation. |
| E2E | Full existing Playwright suite across desktop, tablet and mobile. |
| Platform | Live Docker frontend/API health, route HTTP responses and real-data browser smoke. |
| Performance | No page-level horizontal overflow; no unbounded browser audit waits. |
| Logs/Audit | Zero unexpected browser console/page errors or failed same-origin API responses; recent frontend logs have no fatal/uncaught/500 signature. |

## Fixtures

- Existing deterministic Playwright route fixtures.
- Current local PostgreSQL-backed runtime data for read-only route smoke.
- Viewports: desktop 1440×900, tablet 1024×768 and mobile 390×844.

## Commands

```text
cd apps/web && npm run lint
cd apps/web && npx tsc --noEmit
cd apps/web && npm test -- --run
cd apps/web && npm run build
cd apps/web && E2E_BASE_URL=http://localhost:13000 npm run test:e2e
docker compose ps
```

## Acceptance Evidence

- The first standard Playwright launch failed before collecting tests with `EACCES` while unlinking
  the workspace-local `test-results/.last-run.json`; the directory was a stale root-owned Docker
  artifact. Browser artifacts now default to `/tmp/business-ai-agents-playwright-results`, with a
  `PLAYWRIGHT_OUTPUT_DIR` override and a focused configuration regression test.
- The first full browser run then found one real responsive defect: opening the Graph inspector at
  1280 px produced a 1287 px document. Repeated red proof identified `.card.detail-panel` as the
  overflowing child; the inspector and its direct children now honor the available grid width.
  The focused desktop regression passes five consecutive runs.
- Sequential static and production checks pass: ESLint, TypeScript, 29 Vitest files / 122 tests and
  the Next.js 15.5.20 production build with all 14 routes.
- The complete Playwright command passes 66 tests; six authorization cases are expected skips in
  the current local runtime because auth and E2E credentials are disabled. The separate prior
  enabled-auth proof remains 6/6.
- An independent real-data browser audit checked 13 routes at desktop, tablet and mobile sizes
  (39 route/viewport combinations): zero failed route responses, page/console errors, failed
  same-origin API responses, untranslated badge keys or document-level horizontal overflow.
- PostgreSQL remains healthy; API, worker and frontend remain running on ports 18000/13000. API
  health and frontend `/` return HTTP 200, and recent frontend logs contain no error, exception,
  traceback, fatal or HTTP 500 signature.
