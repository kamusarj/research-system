# Validation

## Proof Strategy

Prove the configured and effective frontend proxy timeout is 180 seconds, exceeds the captured
131.115-second success, preserves current error handling and builds/runs cleanly.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Default, positive override, zero/invalid fallback. |
| Integration | Compose exposes the value to frontend runtime. |
| E2E | Existing document edit/retry/review flows remain green. |
| Platform | Recreated frontend reports `API_PROXY_TIMEOUT_MS=180000`; health remains OK. |
| Performance | Budget exceeds captured 131.115-second successful API duration. |
| Logs/Audit | Root cause correlates one frontend reset with one API HTTP 200; no bodies logged. |

## Fixtures

- Captured request ID `7183a8eb-498d-47b6-8d8c-f359d57de389` metadata only.
- Deterministic Next config inputs.

## Commands

```text
cd apps/web && npm run test -- --run lib/next-config.test.ts hooks/use-document-instant-edit.test.ts
cd apps/web && npm run lint && npm run typecheck && npm run build
docker compose config --quiet
docker compose up -d --build --force-recreate frontend
```

## Acceptance Evidence

- Live log correlation proved request `7183a8eb-498d-47b6-8d8c-f359d57de389` completed successfully
  at DeepSeek and returned API HTTP 200 in 131.115 seconds after the old 125-second frontend proxy
  had already logged `ECONNRESET` / `socket hang up`.
- Next config tests pass 2/2 for the 180,000 ms default, positive override and invalid fallback.
- ESLint, TypeScript, all 110 frontend tests and the 14-route production build pass; build output
  reports `proxyTimeout: 180000`.
- Compose validation passes. The rebuilt/recreated frontend reports
  `API_PROXY_TIMEOUT_MS=180000`, is bound to host port `13000`, and proxied health returns `ok`.
- Document Playwright passes 15/15 across desktop, tablet and mobile.
- A real DeepSeek rename after recreation returned HTTP 200 through `localhost:13000` in 5.7
  seconds with the requested name and review-only patch. Fresh logs contain no socket reset.
