# Session Log

## Context

- User request: Begin implementing the accepted Graph Intelligence upgrade plan; the chatbot may provide a ChatGPT-like experience and call OpenAI directly.
- Agent: Codex
- Date/time: 2026-07-18 10:03 +07

## Work Done

- Files changed:
  - `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
  - `AI_LOGS/DECISIONS.md`
  - `AI_LOGS/HANDOFF.md`
  - `AI_LOGS/TASKS.md`
  - `apps/api/app/models.py`
  - `apps/api/app/api/ontology.py`
  - `apps/api/app/api/graph.py`
  - `apps/api/app/api/router.py`
  - `apps/api/app/schemas/ontology.py`
  - `apps/api/app/schemas/graph.py`
  - `apps/api/app/services/ontology.py`
  - `apps/api/app/services/graph.py`
  - `apps/api/app/seed.py`
  - `apps/api/migrations/versions/8c2d4e6f901a_add_graph_intelligence_ontology.py`
  - `apps/api/tests/test_ontology.py`
- Behavior changed:
  - Added additive persistence for canonical knowledge nodes/edges, aliases, node evidence, graph change sets and ordered mutations.
  - Seeded one deterministic Business AI Agents root and eleven deterministic approved pillars.
  - Added ontology tree, node, children, bilingual search and placement-validation APIs.
  - Added self-parent and ancestor-cycle validation.
  - Added optional graph v2 metadata and `GET /api/v1/graph?view=hierarchy` while keeping `relationship` as the backward-compatible default.
  - Locked the OpenAI graph-chat direction as a server-side, provider-neutral Responses adapter with `store: false`; no chatbot runtime was added in this phase.
- Commands run:
  - `apps/api/.venv/bin/ruff format app tests`
  - `apps/api/.venv/bin/ruff check app tests`
  - `uv run --extra dev python -m pytest -q`
  - `DATABASE_URL=sqlite:////tmp/... uv run python -m alembic upgrade head`
  - `DATABASE_URL=sqlite:////tmp/... uv run python -m alembic downgrade 73f6a8c1d2e0`
  - `DATABASE_URL=sqlite:////tmp/... uv run python -m alembic upgrade head`
  - `git diff --check -- ...`

## Reasoning / Decisions

- Decision: implement the ontology and governed mutation foundation before document upload and chatbot tools.
- Reason: upload mapping and chat proposals both require stable canonical IDs, parent validation, provenance fields and a reviewable change-set boundary.
- Decision: use the accepted eleven-pillar taxonomy with UUIDv5 IDs and one preferred display parent; keep semantic parent edges additive.
- Reason: the hierarchy UI needs deterministic navigation while the knowledge model must still support non-tree relationships.
- Decision: OpenAI may be called directly by the application backend, never directly by browser code; default request storage is disabled.
- Reason: this supports a ChatGPT-like product experience without exposing credentials or giving the model a direct publish/delete path.
- Alternatives considered: implementing the chat UI first was deferred because safe graph writes depend on the later change-set validation/apply service.

## Verification

- Tests/checks:
  - Ruff format and lint.
  - Full backend Pytest suite.
  - Alembic full upgrade, ontology downgrade, then re-upgrade on a temporary SQLite database.
  - Seed row count check and Markdown/diff whitespace check.
- Result:
  - Ruff passed.
  - 47 backend tests passed; one existing Starlette/httpx deprecation warning remains.
  - Migration round trip passed and produced 12 ontology nodes: one root and eleven pillars.
  - `git diff --check` passed.

## Next Agent Notes

- Continue from: Phase 2 frontend hierarchy mode and node detail tabs using `/api/v1/ontology` and `/api/v1/graph?view=hierarchy`.
- Watch out for: the repository has extensive pre-existing user changes and untracked files; do not revert or reformat unrelated work. The checked-in `.venv` launch scripts contain an old absolute path, so run tools through `uv run ... python -m <module>` when a console launcher fails.
- Suggested next command: inspect `apps/web/src` graph API/hooks/canvas/details modules and add the hierarchy switch without replacing the current relationship visualization.
