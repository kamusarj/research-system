# Session Log — Deployed local models completion

## Context

- User request: "Tiếp tục công việc đang dang dở" — read AGENTS.md and the handoff state/log, inspect git
  status/diff and related tests to confirm real progress, then continue the current task and update a
  checkpoint before/after each major implementation step.
- Agent: opencode (deepseek-v4.1-flash-free).
- Date/time: 2026-11-18 16:48 (Asia/Ho_Chi_Minh).

Note: `ai-handoff/STATE.md` and `ai-handoff/LOG.md` do not exist in this repo; the equivalent sources are
`AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, `AI_LOGS/DECISIONS.md`, the story docs under
`docs/stories/deployed-local-models/`, and the Harness DB (`scripts/bin/harness-cli`).

## Work Done

- Files changed:
  - `apps/api/tests/test_local_model_connections.py` — invalid tool calls now assert the established API
    error contract (502 + `{"error":{"code":"CHAT_TOOL_VALIDATION_FAILED"}}` + persisted failed message +
    zero graph change sets); parametrized unknown-tool and non-object-arguments.
  - `apps/api/tests/test_ollama_bridge.py` — compose config test activates `--profile local-ai`; fixed two
    E501 lines.
  - `apps/api/tests/test_ai_collector.py` — Ollama structured test follows the new bounded transport
    (`/api/chat` via `local_models._request`), asserts think/format/temperature.
  - `apps/api/tests/test_ingestion.py` — provider registry expectation includes `local_openai`.
  - `docker-compose.yml` — api/worker env adds `OLLAMA_API_KEY`, `LOCAL_OPENAI_BASE_URL/API_KEY/MODEL`,
    `LOCAL_AI_MAX_RESPONSE_BYTES`; `ollama-bridge` declares `LOCAL_MODEL_BRIDGE_PROTOCOL=ollama`; new
    `local-openai-bridge` service (profile `local-ai`, host network, no ports, read-only, cap-drop ALL).
  - `docker-compose.team.yml` — both bridges use `businessaiagents-team-api:latest` and reset source
    volumes (packaged code).
  - `.env.example` — documented the new local-model env/bridge variables.
  - `README.md` — local-ai runbook now covers both bridges and remote/tunnel upstreams.
  - `apps/web/app/chat/chat-workspace.tsx`, `apps/web/components/chat-local-model-settings.tsx` — explicit
    `aria-label` on the provider/model selects (accessible names were concatenated with option text).
  - `apps/web/e2e/local-chat-models.spec.ts` — exact locators for both selects now that names are explicit.
  - `docs/stories/deployed-local-models/validation.md` — evidence section filled in.
- Behavior changed: invalid/unknown local tool calls fail closed with the standard error envelope; deployment
  can run both bridges with shared server-only config; team builds package bridge code.
- Commands run: targeted pytest, full API pytest, ruff, vitest, typecheck, lint, Playwright (local models +
  chat regression), `docker compose config` (base/team), runtime recreate and health checks, Harness
  trace/story update/complete.

## Reasoning / Decisions

- Decision: keep the established turn-error contract (HTTP error body + persisted `ChatMessage.error_code`)
  instead of returning a 200 `assistant_message`; the new test was the only place deviating from it.
- Decision: bridge services stay behind the optional `local-ai` profile; the compose test must activate the
  profile because `docker compose config` hides profiled services by default.
- Decision: fix E2E locators at the component level with `aria-label` rather than weakening assertions.
- Reason: accessible names derived from wrapping labels include the select's option text, which breaks
  `exact` label matching.
- Alternatives considered: arbitrary-URL local endpoints (rejected: SSRF/credential scope), download-on-demand
  (rejected: disk/not requested), always-on bridges (rejected: optional deployment surface).

## Verification

- Tests/checks:
  - `apps/api`: full pytest suite green; `ruff check` clean.
  - `apps/web`: vitest 44 files / 223 tests; typecheck and eslint clean.
  - Playwright `e2e/local-chat-models.spec.ts`: 6/6 on the live runtime `localhost:13000`
    (desktop/tablet/mobile × ollama/local_openai); `personal-chat-api` + `chat-api-validation`: 6/6.
  - Runtime: api/worker/frontend recreated with new code; health 200; local models route returns 401
    `AUTH_REQUIRED` under local auth.
  - Harness `story complete US-DEPLOYED-LOCAL-MODELS`: pass; story marked implemented.
- Result: all executed checks pass. Fixture inference only — no real model weight was installed or called.

## Next Agent Notes

- Continue from: operator installs an actual Ollama or LM Studio model, sets `OLLAMA_MODEL` /
  `LOCAL_OPENAI_MODEL` + bridge vars, starts `--profile local-ai`, and verifies a real chat/JSON call;
  then Linh reviews the UI and signs acceptance.
- Watch out for: root disk was tight (≈650MB free after clearing the stale `frontend_next` volume and host
  `.next`); the frontend now builds into the `businessaiagents_frontend_next` volume on container start, so
  a source mtime older than the cached build can silently serve stale JS — remove the volume for a clean
  build. Do not prune other projects' images/volumes; keep the `*:pre-hardening-20261103` rollback images.
- Suggested next command: `docker compose --profile local-ai up -d --build ollama-bridge local-openai-bridge`
  then verify in `/chat` with a model the operator has installed.
