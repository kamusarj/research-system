# Validation

## Proof Plan

| Layer | Cases |
| --- | --- |
| Provider | Both protocols; installed/missing/empty models; strict JSON/tool parsing; bounds, redirects, errors, usage |
| API | Inventory/probe; forbidden URL/key override; system-local model selection and pinning; auth/CSRF/rate limit |
| Governance | Unknown tools/invalid args cannot execute; proposals remain draft; no cloud fallback |
| Deployment | Base/team same config; packaged team bridges; allowed routes only; same-host and tunnel fixture |
| UI | Provider/model changes invalidate probe; late response ignored; local inventory/probe/create/reopen; responsive |
| Privacy | Key/endpoint/raw upstream errors absent from response/log; no browser storage of credentials |

## Evidence

Implementation 2026-11-18 (fixture inference only; no model weight installed or downloaded).

- Provider/API: `tests/test_local_models.py` and `tests/test_local_model_connections.py` cover both protocols,
  catalogue/probe keyless + no-store, missing/empty models, strict JSON/tool parsing, endpoint/key override
  rejection, model pinning after operator default change, unknown-tool and non-object-argument fail-closed
  (502 error body + persisted failure message + zero graph change sets), RBAC/CSRF, rate limit, secret-file
  boundary, redaction and usage passthrough.
- Deployment: `tests/test_ollama_bridge.py` covers bounded bridge transport (routes, redirects, compression,
  size/time limits, sanitized upstream errors) and `docker compose config` for base and team overlays with
  profile `local-ai`: api/worker share `OLLAMA_API_KEY`, `LOCAL_OPENAI_*`, `LOCAL_AI_MAX_RESPONSE_BYTES`;
  both bridges are host-network, port-less, read-only, cap-drop ALL, team image with no source volume.
- UI: `components/chat-local-model-settings.test.tsx` + `app/chat/page.test.tsx` (inventory/probe, stale
  response, provider change invalidation); `e2e/local-chat-models.spec.ts` passes 6/6 on the running
  runtime (`localhost:13000`) across desktop/tablet/mobile for both providers: pick installed model,
  verify, create pinned session, reopen after default change, no direct model-server requests from the
  browser, no model name in browser storage.
- Runtime: `api`/`worker`/`frontend` recreated with the new code and env; health 200; `POST
  /chat/connections/local/models` returns 401 `AUTH_REQUIRED` under local auth (route present, RBAC intact).
- Full suites: API pytest 100% green (including legacy collector/registry contracts updated to the new
  transport), web vitest 44 files/223 tests, typecheck, lint and ruff clean.
- Not proven here: a real installed model weight answering end-to-end, and a real remote SSH/VPN model
  host. Those need operator-provided models/endpoints and must be labeled separately.
