# Validation

## Proof Strategy

Use deterministic frontend failures to prove error classification, question retention, explicit
retry and de-duplication. Preserve the existing bounded/non-mutating API proof and verify the live
provider path through the frontend proxy.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Provider timeout, rate limit, malformed response and transport error classification. |
| Integration | Existing brainstorm API remains bounded, redacted and non-mutating. |
| E2E | Failed question remains visible; Retry succeeds without a duplicate user bubble. |
| Platform | Error notice and Retry remain usable at supported viewports. |
| Performance | No automatic retry and no extension of the 120-second deadline. |
| Logs/Audit | Raw provider error is absent from UI; provider outcome remains visible in server telemetry. |

## Fixtures

- First brainstorm call rejects with typed `CHAT_PROVIDER_UNAVAILABLE`; second returns a valid
  DeepSeek response.
- Existing deterministic brainstorm provider double.

## Commands

```text
cd apps/api && .venv/bin/python -m pytest -q tests/test_document_brainstorm.py
cd apps/web && npm run lint && npm run typecheck && npm run test -- --run
cd apps/web && E2E_BASE_URL=http://localhost:13000 npx playwright test e2e/document-upload.spec.ts
```

## Acceptance Evidence

- Live telemetry correlated the reported failure to one DeepSeek provider call ending at 120.3
  seconds with HTTP 503; the frontend proxy did not reset early.
- Deterministic live-Chrome proof against the rebuilt frontend injected the same typed 503, showed
  localized safe copy, exposed Retry, emitted zero raw provider-error strings, called the endpoint
  exactly twice after Retry and kept exactly one visible user question.
- A real DeepSeek request through the frontend proxy for the reported LaTeX name-change scenario
  returned HTTP 200 in 3.3 seconds with the correct `NGUYỄN MINH AN` to `BÙI HOÀNG LINH` guidance.
- Focused component tests pass 15/15; full frontend tests pass 104/104; ESLint, TypeScript and the
  14-route production build pass.
- Focused backend brainstorm tests pass 4/4 with Ruff clean. Document Playwright passes 12/12 at
  desktop, tablet and mobile. The first E2E invocation could not write a stale container-owned
  `test-results/.last-run.json`; rerunning with a fresh temporary output directory passed without
  deleting or changing that existing artifact.
