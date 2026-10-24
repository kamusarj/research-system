# Session Log

## Context

- User request: continue the active goal to finish Graph Intelligence v2 acceptance before Gate C, projection upgrades and Discord.
- Agent: Codex.
- Date/time: 2026-07-21 00:10 +07.

## Work Done

- Files changed: `apps/web/components/document-graph-canvas.tsx`, its unit test,
  `apps/web/app/globals.css`, `Docs/Graph Intelligence v2 Product Acceptance Checklist.md`, the
  `docs/stories/graph-intelligence-v2-acceptance/` high-risk packet, `AI_LOGS/HANDOFF.md`,
  `AI_LOGS/TASKS.md`, and this session log.
- Behavior changed: dense document hierarchy layers wrap into five-column rows with stable ordering
  and expanded height instead of compressing all nodes into one overlapping line. No API, schema,
  credential or provider contract changed.
- Runtime work: rebuilt/restarted only the Research System database/API/worker/frontend on ports
  `18000`/`13000`; preserved PostgreSQL and document-object volumes; did not touch unrelated
  `smart_exam_*` containers.
- Harness work: intake #3 recorded the high-risk provider/acceptance task; story `US-GV2-ACCEPT`
  was created and remains `in_progress` with unit/E2E/platform proof recorded.

## Reasoning / Decisions

- Decision: keep all product-owner checklist boxes unchecked while recording engineering evidence.
- Reason: DEC-020 explicitly reserves workflow acceptance for Linh.
- Decision: retry the persisted Mistral `AI_RESPONSE_INVALID` document job with DeepSeek rather than
  hiding or overwriting the failure.
- Reason: the accepted provider-neutral worker contract makes provider selection explicit and keeps
  typed failures reviewable.
- Decision: edit the one missing-evidence mutation, reject one semantic edge, approve/apply the 65
  remaining mutations and verify repeat-apply idempotency.
- Reason: this exercises the actual governed review contract without allowing unsupported knowledge
  or an unreviewed edge into the canonical graph.
- Decision: fix the dense graph discovered during live inspection before presenting it for acceptance.
- Reason: the previous one-row layout made the 39-node graph materially difficult to inspect.

## Verification

- Backend: Ruff passes; 26 focused document/change-set/chat/hardening tests pass with the known
  Starlette/httpx deprecation warning.
- Frontend: ESLint and TypeScript pass; 24 Vitest tests pass; Next.js production build succeeds for
  all 15 routes; 27 Playwright cases pass across desktop/tablet/mobile.
- Live integration: DeepSeek fixture score 85.75; isolated graph 39 nodes/33 edges; 38 supported and
  one evidence-pending node; change set applied with 65 accepted/one rejected mutation; repeated apply
  retained the original timestamp; rejected edge is absent.
- Runtime: direct/proxied health pass, migration remains `e9f5c2a7d104`, readiness is `ready` with 45
  canonical nodes/32 edges and no invariant errors, and current post-restart service logs are clean.
- Markdown/code: scoped `git diff --check` passes.
- Harness: detailed trace #3 meets the high-risk tier. Audit entropy is `5/100` solely because
  `US-GV2-ACCEPT` correctly remains unverified until real OpenAI chat and product-owner acceptance.

## Known Issues

- The configured OpenAI credential is still rejected. The real application turn persists a safe
  assistant `CHAT_PROVIDER_UNAVAILABLE` with no provider response ID or graph change set; no secret
  value was read or logged.
- Mistral produced invalid structured document-graph analysis for the acceptance fixture after a
  valid paper-fit response. DeepSeek retry succeeded; automatic fallback policy is not yet decided.
- During an interrupted runtime stop, the still-running worker logged temporary database DNS
  tracebacks. The worker recovered after a clean restart and the post-restart window is clean.
- Product-owner usability, error wording, rate-limit wording and rollout decision remain human checks.

## Next Agent Notes

- Continue from: install a valid OpenAI secret through environment/secret management, recreate only
  the API service as needed, run one scoped brainstorm and one grounded draft proposal, then ask Linh
  to complete the unchecked product-owner checklist.
- Watch out for: never store credentials in Git, Harness traces or `AI_LOGS`; do not self-mark product
  acceptance; preserve the applied acceptance fixture and the dirty worktree.
- Suggested next command: `scripts/bootstrap-harness.sh` followed by
  `scripts/bin/harness-cli query matrix --active --summary`.
