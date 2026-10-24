# Session Log

## Context

- User request: continue immediately with Graph Intelligence v2 Phase 6.
- Agent: Codex.
- Date/time: 2026-07-18 13:15 +0700.

## Work Done

- Files changed: added runtime-control config/middleware, system feature/readiness APIs and schemas, graph invariant service/CLI, deterministic placement and near-duplicate services, release evaluation runner, migration-parity script, Phase 6 backend tests, Make targets, Compose/env settings, evaluation report, operations runbook, product acceptance checklist, plan/README and AI logs.
- Behavior changed: provider pillar labels are canonicalized with deterministic fallback; near-duplicate workspaces become review context; v2 surfaces can be rolled back independently; costly mutations are rate-limited; responses expose timing; graph readiness checks invariants; evaluation/migration/backup gates are repeatable.
- Commands run: Ruff, full Pytest, ESLint, Vitest, Next build, gold evaluation, SQLite migration parity, PostgreSQL `alembic check`, graph invariant CLI/API, isolated PostgreSQL dump/restore/count comparison/cleanup, Compose rebuild, runtime health/features/readiness/log checks, Playwright desktop/tablet/mobile, Compose config and `git diff --check`.

## Reasoning / Decisions

- Decision: use deterministic server-side placement and duplicate safeguards as provider-independent release regressions without changing the accepted weighted rubric.
- Reason: fixture gates must remain reproducible even when a cloud credential is unavailable, while provider outputs still require validation and human review.
- Alternatives considered: direct provider-only evaluation was not used as the release gate because it is non-deterministic and the current OpenAI credential is rejected; a Redis limiter was deferred because this remains a single-process local MVP; automated product acceptance was rejected because only the product owner can approve usability.

## Verification

- Tests/checks: 85 backend tests, 23 frontend tests, 27 E2E cases, lint/build, 30-item gold metrics, migration parity, live graph invariants, PostgreSQL schema drift, backup/restore drill, runtime health/logs.
- Result: all engineering gates pass. Gold routing/placement/duplicate metrics are 1.00 with zero fixture failures; PostgreSQL is at `e9f5c2a7d104`; readiness is `ready`; the rebuilt stack runs at frontend `13000` and API `18000`; Smart Exam containers were untouched. The temporary restore database and dump were removed.

## Next Agent Notes

- Continue from: replace the invalid OpenAI secret and guide Linh through the product acceptance checklist.
- Watch out for: never store the replacement key in Git/AI logs; rate limiting is local-process only; deterministic fixture metrics are not real-traffic accuracy; do not self-mark product-owner acceptance.
- Suggested next command: `curl --fail http://localhost:18000/api/v1/system/readiness`.
