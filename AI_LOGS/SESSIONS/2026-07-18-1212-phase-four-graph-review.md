# Session Log

## Context

- User request: rebuild the Research System and continue with the next implementation step.
- Agent: Codex.
- Date/time: 2026-07-18 12:12 +07.

## Work Done

- Files changed:
  - Backend: `apps/api/app/api/{documents,graph_changes,ontology,router}.py`, `apps/api/app/schemas/graph_changes.py`, `apps/api/app/services/{graph_changes,ontology_mapping}.py`, and `apps/api/tests/test_graph_changes.py`.
  - Frontend: `apps/web/app/graph/changes/**`, `apps/web/components/graph-change-review*`, document detail create-change-set action, graph-change client/types, app navigation, bilingual messages, responsive styles, and Playwright coverage.
  - Handoff: `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md`, and this session log.
- Behavior changed:
  - Reviewable document graphs can generate idempotent document-to-canonical change sets.
  - Exact canonical/approved-alias matches propose evidence attachment; fuzzy matches remain reviewer-visible candidates and never auto-merge.
  - Validation covers grounded evidence, label/type/parent validity, approved endpoints, duplicate nodes, controlled relations, confidence, self-loops and proposed hierarchy cycles.
  - Reviewers can edit, accept or reject each mutation, validate/approve/reject the set, apply accepted mutations atomically and idempotently, and create a compensating change set.
  - `/graph/changes` provides a bilingual responsive queue and source/canonical diff with candidate and evidence context. Reviewable document pages link into this flow.
  - Rebuilt and recreated the database/API/worker/frontend stack on API `18000` and frontend `13000`; existing PostgreSQL/object volumes were preserved.
- Commands run:
  - `API_PORT=18000 FRONTEND_PORT=13000 API_CORS_ORIGINS=http://localhost:13000 docker compose up -d --build database api worker frontend` (initial rebuild and final source-complete rebuild).
  - `uv run ruff check app tests`.
  - `docker compose exec -T api python -m pytest -q` after temporarily installing Pytest into the pre-final API container.
  - `npm run lint`, `npm run test -- --run`, `npm run build`.
  - `E2E_BASE_URL=http://localhost:13000 npm run test:e2e`.
  - Runtime health, candidate/change-set API, frontend route, Compose status/log and Alembic-head smoke checks.
  - `git diff --check`.

## Reasoning / Decisions

- Decision: only an exact normalized canonical label or approved alias may map directly to an existing node; similarity is candidate evidence for a human decision, not an automatic merge.
- Reason: this avoids silent concept collapse while still surfacing likely duplicates during graph review.
- Decision: canonical nodes and edges are written only by the approved change-set apply service, in one transaction with a row lock and idempotent target IDs/evidence copying.
- Reason: document AI output must remain isolated until explicit approval, and retries must not duplicate published knowledge.
- Decision: undo is represented by a new compensating change set that archives created nodes and supersedes created edges; accepted knowledge is not hard-deleted.
- Reason: the accepted v2 plan excludes delete and requires an auditable reversible workflow.
- Alternatives considered: direct document merge and similarity-based auto-merge were rejected by the accepted governance boundary.

## Verification

- Tests/checks:
  - Ruff: pass.
  - Backend: 71 tests pass; one known upstream Starlette/httpx deprecation warning.
  - Frontend: ESLint pass, 22 Vitest tests pass, Next.js production build pass.
  - Browser: 24 Playwright cases pass across desktop, tablet and mobile, including the complete accept → approve → apply graph-change flow.
  - Runtime: API/worker/frontend/database up; PostgreSQL healthy; Alembic `d7e3b9a1f604 (head)`; direct/proxied `/api/v1/health` 200; graph-change list, ontology candidates and `/graph/changes` healthy; clean startup logs.
  - Safety: all `smart_exam_*` containers remained running and untouched.
- Result: Phase 4 exit gates pass: document AI cannot bypass review, accepted mutations appear only after apply, rejected mutations are excluded, and repeat apply is idempotent.

## Next Agent Notes

- Continue from: Phase 5 graph-aware brainstorm chatbot.
- Watch out for:
  - The host `apps/api/.venv` has stale pre-monorepo interpreter/shebang paths; recreate it before relying on host `uv run pytest`, or use an ephemeral dev test environment.
  - The Compose API image intentionally installs runtime dependencies only, so Pytest is absent after the final rebuild.
  - OpenAI graph-chat calls must use strict server-side tools, bounded context/tool loops and `store: false`; chat must never receive publish/delete or unrestricted access.
- Suggested next command: inspect the existing AI provider/Responses adapter and add additive chat persistence plus strict provider-neutral read/propose schemas before exposing `/chat`.
