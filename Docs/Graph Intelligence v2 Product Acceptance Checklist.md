# Graph Intelligence v2 Product Acceptance Checklist

Date prepared: 2026-07-18  
Product owner: Linh  
Engineering state: ready for acceptance through the configured DeepSeek graph-chat provider; OpenAI
switchback remains optional follow-up work.

## Automated evidence

- [x] Paper-fit routing regression meets the accepted threshold.
- [x] Top-three canonical-pillar placement regression meets the accepted threshold.
- [x] Near-duplicate recall meets the accepted fixture threshold.
- [x] Canonical graph invariant check reports no cycles, dangling endpoints or duplicate keys.
- [x] Migration upgrade/downgrade/upgrade and model parity checks pass.
- [x] Existing research, search and relationship graph routes remain in the E2E hydration suite.
- [x] Upload, hierarchy, change review and chat UI have desktop/tablet/mobile coverage.
- [x] Rate limits, performance timing headers and typed feature-disabled behavior are tested.
- [x] Backup/restore and rollback procedures are documented.

## Product-owner walkthrough

- [ ] Upload a text-layer PDF/Markdown/text document and confirm the evaluation is understandable.
- [ ] Inspect its isolated graph, parent-child navigation and node evidence.
- [ ] Create a mapping change set, reject one mutation, approve/apply the rest and inspect history.
- [ ] Open a scoped chat, brainstorm one useful concept, and confirm the proposal is draft-only.
- [ ] Review and apply a grounded chat proposal; confirm no unapproved mutation appears in graph.
- [ ] Check desktop, tablet and mobile usability in the preferred language.
- [ ] Confirm error/retry wording is acceptable for provider failure and rate limiting.
- [ ] Approve rollout or record required changes below.

## Engineering-assisted walkthrough evidence

These results were produced on 2026-07-21 to prepare the product-owner walkthrough. They do not
mark any product-owner checkbox or substitute for Linh's usability and rollout decision.

- The current worktree was rebuilt and the four core services became healthy on API `18000` and
  frontend `13000`. Readiness remained `ready`; the canonical graph contained 45 valid nodes and 32
  valid edges with no invariant errors after the walkthrough.
- Markdown workspace `de618dc2-6f87-4eff-a785-1665a229f9c4` completed with DeepSeek
  `deepseek-v4-pro`: fit score `85.75`, `priority_review`, 39 isolated nodes, 33 isolated edges, 38
  supported nodes and one explicit `evidence_pending` node. Parent links had one document root and
  no dangling parent; the canonical breadcrumb became `Business AI Agents` →
  `Data, Knowledge & Memory` → `Evidence-Grounded Memory Architecture`.
- Mistral produced a valid paper-fit evaluation first but invalid structured graph analysis. The
  persisted typed `AI_RESPONSE_INVALID` failure was retried with DeepSeek and completed, giving the
  product owner a real provider-failure/retry case to review.
- Structured document-graph prompt v2 now retries one Pydantic validation failure with the same
  selected provider and a bounded integrity checklist; it never substitutes a provider or persists
  an invalid partial graph. A new live Mistral workspace
  `c91507a7-d186-418c-9202-34220ec75dfd` completed on its first structured response at score `74.5`
  with 20 supported nodes, 14 edges and zero dangling endpoints. Deterministic tests prove the
  invalid→valid recovery and invalid→invalid terminal-error paths.
- Change set `d7dc15e4-bfb3-4c8c-a615-553c0359827d` initially found one missing-evidence error. The
  mutation was grounded with source evidence, one normalized semantic edge was explicitly rejected,
  and 65 remaining mutations were approved/applied. Repeated apply preserved the original timestamp,
  history reports `65 accepted / 1 rejected`, and the rejected edge is absent from the canonical graph.
- A dense-graph usability finding was fixed during the walkthrough: large hierarchy layers now wrap
  into stable rows instead of compressing 39 nodes into one overlapping line. The current live page
  was visually inspected on desktop and mobile after rebuild.
- Current verification after the source-neutral intake and acceptance-preflight work: all 165
  backend tests plus Ruff pass; frontend ESLint and TypeScript pass; 28 Vitest tests pass; the
  production build generates all 15 routes; and 30 Playwright cases pass across desktop, tablet and
  mobile with six auth-only skips in trusted-local mode.

## Provider transition evidence

The configured OpenAI credential was rechecked through the real graph-chat application path. Session
`08ce0746-e28c-4682-be1a-e66943795aac` persisted a user message followed by a safe assistant failure
with `CHAT_PROVIDER_UNAVAILABLE`, no provider response ID and no graph change set. The server returned
HTTP 503 because the upstream credential was rejected; both real-chat walkthrough items remain
blocked until the secret is replaced. A later minimal graph-scope recheck in session
`651f826e-24d0-4341-bbdf-5aa3c5121056` produced the same typed 503 with no request/response ID or
change set. No key value is stored in this checklist or AI logs.

The OpenAI API path remains healthy and chat-enabled on the official `gpt-5.6-luna` model, but a fresh
minimal Responses request still returned upstream HTTP 401 with a request ID. The new
`python -m app.operations verify-openai` preflight reproduces the application result as typed
`CHAT_PROVIDER_UNAVAILABLE` while exposing no key, prompt, provider output, ID value or upstream
body.

On 2026-07-21 Linh explicitly authorized the already configured DeepSeek provider as the temporary
graph-chat default so acceptance is no longer gated by OpenAI. Decision 0016/DEC-029 preserves the
OpenAI adapter and makes later switchback configuration-only. DeepSeek uses native Chat Completions
tool calls in non-thinking mode; bounded context/redaction, server-side Pydantic argument validation,
read/propose-only tools and draft change-set review/apply governance are unchanged.

`python -m app.operations verify-chat-provider` checks the configured default without printing key,
prompt, provider output or ID values. `scripts/verify_graph_v2_acceptance.sh` now prevents accidental
story completion until the selected provider preflight passes, every walkthrough item is checked and
Linh records exactly one accepting decision below.

The rebuilt runtime now reports DeepSeek `deepseek-v4-pro` as the configured active graph-chat
provider. Adapter tests, all 168 backend tests, 28 frontend tests, the production build and 30
desktop/tablet/mobile E2E cases pass. The earlier host/container TCP timeout was transient:
API-container reachability subsequently recovered and `verify-chat-provider` returned `ready` for
`deepseek-v4-pro` without exposing any secret, provider content or ID value.

A real graph-scoped DeepSeek session searched the canonical graph and loaded node context; broad
turns that exhausted the tool budget stopped safely at `CHAT_TOOL_LOOP_LIMIT`, and an ungrounded
proposal remained invalid. A clean document-scoped session then used the governed
`create_change_set` and `propose_node` tools with evidence retrieved from the uploaded document.
Change set `5759af2f-4685-4cfa-b360-39d7981a1fa4` is now `needs_review`; its single
`Cited Recommendation Review Gate` mutation is evidence-supported and valid, with zero errors or
warnings. No canonical node was approved or applied. This engineering evidence does not mark either
chat walkthrough checkbox; Linh still reviews the actual wording, proposal and apply behavior.

## Product-owner decision

- [ ] Accepted.
- [ ] Accepted with follow-up work.
- [ ] Changes required.

Notes:

```text

```
