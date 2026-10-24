# Session Log

## Context

- User request: Continue the active completion goal after reading `AI_LOGS`; implement the accepted
  source-neutral intake receipt prerequisite before Discord and manage the work through Harness.
- Agent: Codex
- Date/time: 2026-07-21 12:15 +07

## Work Done

- Files changed: additive receipt/service-account models and migration; auth identity/schema/API;
  source-neutral receipt API/service; document atomic-record helper; legacy ingestion dual-write;
  rate/feature controls; receipt, migration and real-MinIO proof tests/scripts; architecture,
  completion, pipeline, operator and story documentation; AI handoff/task/decision logs.
- Behavior changed: manual/API/platform occurrences are durable independently from URL/document
  processing aggregates. Replays converge; repeated occurrences keep provenance; document success
  requires object-store read-back plus database commit; adapter bearer tokens are hashed/revocable
  and namespace-scoped. Discord was not implemented.
- Commands run: Harness bootstrap/intake/story/trace/audit; Ruff and full Pytest; deterministic
  migration verifier and Alembic parity; disposable real MinIO proof; PostgreSQL dump validation and
  restore drill; final Docker image rebuild/recreate; direct/proxied health and readiness; frontend
  ESLint/TypeScript/Vitest/build; full Playwright across three viewports; Compose validation.

## Reasoning / Decisions

- Decision: implement DEC-028 additively and preserve existing processing aggregates/legacy columns.
- Reason: provenance identity and processing identity have different deduplication semantics; this
  is the safe application prerequisite for any future Discord adapter.
- Alternatives considered: deriving receipt identity from URL/content or embedding Discord logic in
  the worker were rejected by the accepted spec because they lose occurrences or duplicate business
  logic.

## Verification

- Tests/checks: 163 backend tests; Ruff; deterministic backfill/downgrade-refusal verifier;
  Alembic no-diff downgrade/upgrade parity at `a8b4c6d2e913`; `INTAKE_RECEIPT_SPEC_OK`; real MinIO
  `INTAKE_RECEIPT_MINIO_OK`; 28 frontend tests plus lint/type/build; 30 Playwright passes with six
  expected local-auth skips; direct/proxied health and graph readiness.
- Result: pass. Main runtime is healthy with 39 receipts / 39 items / 27 canonical URL jobs, zero
  missing URL references, 8 research rows, 3 document workspaces and valid 45-node/32-edge graph.
  Harness story `US-INTAKE-RECEIPTS-IMPLEMENT` is implemented; detailed trace #17 meets the
  high-risk requirement; audit remains 5/100 only for the open acceptance story.

## Next Agent Notes

- Continue from: replace the rejected OpenAI credential, execute a real scoped chat turn, and have
  the product owner record Graph v2 acceptance in the prepared checklist.
- Watch out for: do not start Discord until target-environment Gate C operations and Gate D
  guild/channel/attachment/token/rate/status-reply ownership are accepted. Do not put service tokens
  or platform credentials in source control or `AI_LOGS`.
- Suggested next command: `scripts/bin/harness-cli query matrix --active --summary`
- Temporary recovery artifact: `/tmp/business-ai-pre-receipts.dump` and `.list` remain inside the
  current database container after a successful restore drill; copy them to an authorized backup
  location before replacing that container if the pre-migration recovery point must be retained.
