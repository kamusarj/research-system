# Validation

## Proof Strategy

Prove the proxy budget exceeds the API AI budget, malformed provider output is typed, error mapping
and Retry are deterministic, and simplification preserves import/edit/preview/brainstorm/cache/create
behavior across supported viewports.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Malformed provider payload; code/status-to-message and retry classification. |
| Integration | Typed 502 response; no persistence or content logging regression. |
| Component | Transient failure shows Retry; retry succeeds; no-change is friendly and not retryable; preview starts collapsed and modes remain. |
| E2E | Select text, edit, Undo, preview disclosure and zero horizontal overflow. |
| Platform | Desktop, tablet and mobile; proxy setting present in production build/runtime. |
| Logs/Audit | Slow success reaches browser; recent logs have no proxy socket reset or untyped 500. |

## Fixtures

- Provider double raising malformed-payload exceptions.
- First-call transient error followed by successful edit.
- Markdown/LaTeX authoring draft with collapsed preview.

## Commands

```text
cd apps/api && uv run ruff check app tests && uv run python -m pytest -q
cd apps/web && npm run lint && npm run typecheck && npm run test -- --run && npm run build
cd apps/web && E2E_BASE_URL=http://localhost:13000 npx playwright test e2e/document-upload.spec.ts
```

## Acceptance Evidence

- Root cause correlated from live logs: one DeepSeek request completed successfully at the API in
  33,773 ms after Next.js's default 30,000 ms rewrite proxy had reset the browser socket.
- Production configuration and unit proof set `experimental.proxyTimeout` to 125,000 ms, above the
  API's 120-second provider budget.
- Ruff and all 295 backend tests pass. A malformed provider choices payload now returns typed
  `AI_RESPONSE_INVALID` / HTTP 502 instead of escaping as HTTP 500.
- ESLint, TypeScript, all 99 frontend tests and the 14-route production build pass. Tests cover
  transient/no-change/auth error mapping, one user-triggered Retry, and preview collapsed by default.
- Playwright passes 9/9 document cases across desktop, tablet and mobile, including editable import,
  preview disclosure/modes, brainstorm, direct selection editing, Undo and zero horizontal overflow.
- Rebuilt runtime is healthy on API `18000` / frontend `13000`. A real 1,175-character DeepSeek
  shortening request through the frontend proxy returned HTTP 200 in 13,820 ms; recent API/worker/
  frontend logs contain no socket reset, untyped HTTP 500, traceback, exception or fatal entry.
- Chrome at 1920×1080 visually confirms the compact editor-led page: one-line page heading, compact
  create form, editor + AI, collapsed binary upload, collapsed preview and the existing document
  list. `git diff --check` passes.
- Harness story completion reran the entire proof command successfully.
- Detailed Harness trace #45 meets the required high-risk tier 3/3.
