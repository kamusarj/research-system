# Validation

## Proof Strategy

Combine live runtime/API evidence with existing deterministic regression gates. Automated checks may
prove technical behavior, but only Linh can mark the product-owner decision.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Existing paper-fit, placement, duplicate, graph-change and chat orchestration suites. |
| Integration | Health/readiness, secret-safe selected-provider preflight, real document processing, isolated graph/evidence, change-set lifecycle, scoped chat and provider failure. |
| E2E | Upload, hierarchy, change review and chat on desktop/tablet/mobile in EN/VI. |
| Platform | Compose startup, migration head, preserved volumes, feature flags and clean service logs. |
| Performance | `X-Process-Time-Ms`, `Server-Timing`, rate-limit headers and typed HTTP 429. |
| Logs/Audit | No credentials or request bodies; provider/model/request provenance and typed errors remain available. |

## Fixtures

- A deterministic UTF-8 Markdown document about an accepted Business AI Agents topic.
- Existing eleven-pillar ontology and canonical root.
- A local chat session scoped to the uploaded document or graph root.
- Existing configured AI providers; the selected graph-chat provider must be valid for the real chat portion.

## Commands

```text
API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 docker compose up -d database api worker frontend
curl --fail http://localhost:18000/api/v1/health
curl --fail http://localhost:18000/api/v1/system/features
curl --fail http://localhost:18000/api/v1/system/readiness
docker compose exec -T api alembic current
docker compose exec -T api python -m app.operations verify-graph
docker compose exec -T api python -m app.operations verify-chat-provider
docker compose exec -T api python -m app.operations verify-openai
bash scripts/verify_graph_v2_acceptance.sh
DEEPSEEK_API_KEY_SECRET_FILE=/dev/null docker compose -f docker-compose.yml -f docker-compose.deepseek-secret.example.yml config --quiet
OPENAI_API_KEY_SECRET_FILE=/dev/null docker compose -f docker-compose.yml -f docker-compose.openai-secret.example.yml config --quiet
```

The acceptance verifier accumulates runtime, graph, provider and human-checklist results rather
than stopping at the first failure. It cannot pass until selected-provider access succeeds, every walkthrough
item is checked, and exactly one accepting product-owner decision is recorded. It never modifies
the checklist.

## Acceptance Evidence

Engineering-assisted execution completed on 2026-07-21; final product-owner acceptance remains
pending.

- Platform: current API image rebuilt; PostgreSQL is at `a8b4c6d2e913 (head)`; direct and proxied
  health return 200; readiness reports `ready` and valid graph invariants. The persisted acceptance
  fixture survived service restarts.
- Provider boundary: the OpenAI credential is configured but real application turns returned the
  safe typed `503 CHAT_PROVIDER_UNAVAILABLE`. Recheck session
  `651f826e-24d0-4341-bbdf-5aa3c5121056` also produced no provider request/response ID or change set.
  No credential value or upstream body was printed.
- Current credential recheck: the API is healthy and chat-enabled on `gpt-5.6-luna`, but a fresh
  minimal direct Responses probe still returned upstream HTTP 401 with an OpenAI request ID. The
  secret is not file-mounted in the local runtime. The new operator preflight preserves the same
  application adapter behavior while printing only typed/boolean allowlisted fields.
- Document integration: Mistral paper-fit succeeded but structured graph analysis failed with
  `AI_RESPONSE_INVALID`; a DeepSeek retry completed at score `85.75` with 39 nodes and 33 edges.
- Evidence/hierarchy: 38 nodes were supported, one remained `evidence_pending`, all 38 parent links
  resolved to the single document root, and the applied canonical node produced the expected
  root/pillar/node breadcrumb.
- Change governance: one missing-evidence mutation was edited with grounded evidence, one edge was
  rejected, 65 mutations were approved/applied, repeat apply was idempotent, and readiness remained
  valid at 45 nodes and 32 edges.
- UI finding/fix: dense hierarchy layers now use deterministic five-column wrapping with expanded
  height; a 12-child regression test proves three distinct rows. Live desktop/mobile screenshots were
  inspected after rebuilding the frontend.
- Automated proof: Ruff and all 165 backend tests pass; frontend ESLint, TypeScript, 28 Vitest tests
  and the 15-route production build pass; 30 Playwright tests pass on desktop/tablet/mobile with six
  expected auth-only skips in trusted-local mode. The executable Harness verification reaches its
  final gate and fails only on the current provider access and unchecked human acceptance markers.
- Log evidence: the current post-restart window has no API/worker/frontend HTTP 500, traceback,
  exception or fatal entries. Earlier worker DNS tracebacks correspond to the database/network being
  stopped during the interrupted acceptance run and precede the clean worker restart.
- DeepSeek transition proof: decision 0016 and DEC-029 authorize the temporary provider. The adapter
  translates native assistant tool calls and `tool_call_id` results, disables thinking, withholds
  local metadata, normalizes usage and retains application-side Pydantic validation. Ruff and all
  168 backend tests pass; frontend lint/typecheck, 28 tests and build pass; 30 E2E cases pass with six
  expected auth skips. Rebuilt API/frontend are healthy and DeepSeek is `chat_active`.
- Live DeepSeek acceptance proof: on 2026-07-25 API-container TCP/443 reachability recovered and
  `python -m app.operations verify-chat-provider` returned `ready` for `deepseek-v4-pro`, with
  output/response-ID presence and no secret, prompt, provider text or ID value printed. A real
  graph-scoped brainstorm session exercised bounded graph search/context tools and safely rejected
  an ungrounded proposal. A document-scoped follow-up retrieved real source evidence, then used
  `create_change_set` and `propose_node` to create review change set
  `5759af2f-4685-4cfa-b360-39d7981a1fa4`. Its single mutation is evidence-supported and valid, with
  zero errors or warnings. No canonical mutation was approved or applied.

Remaining proof:

- Keep OpenAI switchback pending until its separate credential preflight succeeds.
- Linh reviews the real UI, provider/retry wording and rate-limit wording, then records the product
  decision in the checklist.
