# DeepSeek Graph Chat Transition

## Context

- User request: use DeepSeek temporarily to finish Graph Intelligence v2 chat acceptance, preserve
  later OpenAI switchback, reset the completion goal and continue.
- Agent: Codex `/root`.
- Date/time: 2026-07-21 13:10 +0700.

## Work Done

- Implemented DeepSeek native Chat Completions tool calling behind the existing graph-chat provider
  protocol, using non-thinking mode and the existing bounded read/propose tool loop.
- Added configurable `GRAPH_CHAT_DEFAULT_PROVIDER`, generic `verify-chat-provider`, a narrow
  DeepSeek secret overlay and UI selection between configured DeepSeek/OpenAI providers.
- Preserved OpenAI Responses, `verify-openai`, local persistence, redaction, Pydantic tool validation,
  draft change sets and human review/apply authority.
- Recorded Harness intake #14 and decision 0016 plus DEC-029; updated acceptance docs and verifier.
- Rebuilt only API/frontend and preserved PostgreSQL/object volumes; no `smart_exam_*` service was
  touched.

## Files Changed

- Backend/config/tests: `apps/api/app/core/config.py`, `apps/api/app/schemas/chat.py`,
  `apps/api/app/services/ai.py`, `apps/api/app/services/graph_chat.py`,
  `apps/api/app/services/providers/openai_graph_chat.py`, `apps/api/app/operations.py`, and focused
  backend tests.
- Frontend/tests: `apps/web/app/chat/page.tsx`, `apps/web/app/chat/page.test.tsx`,
  `apps/web/lib/types.ts`, `apps/web/lib/i18n.tsx`.
- Operations/docs: `.env.example`, `docker-compose.yml`, both managed-secret examples,
  `scripts/verify_graph_v2_acceptance.sh`, README, Graph v2 plan/runbook/checklist/story packet,
  decision 0016, DEC-029 and AI logs.

## Decisions Made

- DeepSeek is the temporary default; OpenAI remains available and switchback is environment-only.
- DeepSeek thinking is disabled so no reasoning content needs to be persisted or replayed.
- DeepSeek strict beta is not used because its schema subset rejects constraints in current tool
  schemas; all tool arguments continue through mandatory application-side Pydantic validation.
- No acceptance checkbox is self-marked and Gate C/Discord do not start before the real provider and
  product-owner gates pass.

## Commands/Tests Run

- Harness bootstrap, intake #14, decision/story updates and active matrix checks.
- `uv run --frozen ruff check app tests scripts`
- `uv run --frozen python -m pytest -q` — 168 passed.
- `npm run lint && npm run typecheck && npm test && npm run build` — 28 tests and 15 routes passed.
- `E2E_BASE_URL=http://localhost:13000 npm run test:e2e` — 30 passed, 6 trusted-local auth skips.
- Base, DeepSeek-secret and OpenAI-secret Compose validation; `git diff --check`.
- API/frontend Docker rebuild; health/readiness/provider registry and clean-log checks.
- Real `verify-chat-provider` with `deepseek-v4-pro` and isolated `deepseek-v4-flash`.

## Verification Result

- Code, deterministic integration, UI/build, E2E, Compose and rebuilt runtime checks pass. Runtime
  is ready with 45 valid nodes and 32 edges; DeepSeek is configured and `chat_active`.
- Live provider proof is incomplete: DNS resolves, but TCP connection to
  `api.deepseek.com:443` times out from both host and API container. Both model preflights return
  typed `CHAT_PROVIDER_UNAVAILABLE`; no HTTP response, secret, provider body or ID value was exposed.
- The acceptance verifier reports runtime/graph OK and provider/walkthrough/product-decision pending.
- Harness detailed trace #20 meets the required high-risk 3/3 tier.
- Harness audit entropy is `0/100`; `git diff --check` and Markdown fence checks pass.

## Known Issues

- Restore host/container egress to DeepSeek before claiming a real governed chat proposal.
- Linh must still complete the product-owner walkthrough and record exactly one decision.
- The goal service retained the old `blocked` goal and rejected creating a replacement as unfinished;
  repository execution nevertheless resumed under the same completion objective.

## Next Best Action

1. Restore TCP/443 reachability to `api.deepseek.com` without storing credentials in source/logs.
2. Run `docker compose exec -T api python -m app.operations verify-chat-provider`.
3. Run a scoped DeepSeek brainstorm and grounded proposal, review/apply it, then rerun
   `scripts/verify_graph_v2_acceptance.sh` and complete Linh's checklist.
