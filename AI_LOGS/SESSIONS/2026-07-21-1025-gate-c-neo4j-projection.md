# Session Log

## Context

- User request: continue the active completion goal after reading `AI_LOGS`; finish the next safe
  project work while OpenAI credential/product-owner acceptance remains externally blocked.
- Agent: Codex `/root`.
- Date/time: 2026-07-21 10:25 +07.

## Work Done

- Files changed:
  - Added `apps/api/app/services/neo4j_projection.py`,
    `apps/api/tests/test_neo4j_projection.py` and
    `apps/api/scripts/verify_neo4j_projection.py`.
  - Updated graph repository/routes, configuration, error handling, observability, auth policy test,
    API dependency lock, Compose/secret examples and README.
  - Added Harness story packet `docs/stories/gate-c-neo4j/`, durable decision
    `docs/decisions/0012-idempotent-neo4j-projection.md`, intake #9 and completed story
    `US-GATEC-NEO4J`.
  - Updated Research System completion/architecture/implementation and Graph v2 planning docs plus
    `AI_LOGS/HANDOFF.md`, `AI_LOGS/TASKS.md` and `AI_LOGS/DECISIONS.md`.
- Behavior changed:
  - `GRAPH_DATA_PROVIDER=neo4j` now provides real validated, bounded relationship/hierarchy reads,
    shortest path and cluster behavior instead of a 501 scaffold.
  - Owner-only `POST /api/v1/graph/rebuild` atomically replaces both views from one PostgreSQL
    snapshot with composite constraints, parameterized batches and stale-row pruning.
  - Neo4j is an optional internal-only digest-pinned Compose profile with separate API/server secret
    files; failures are typed, fail-visible and never fall back to PostgreSQL.
  - Recreated only the main API/worker containers after the old image lacked the new driver. Main
    data, database, frontend and unrelated `smart_exam_*` services were preserved.
- Commands run:
  - Harness bootstrap/intake/story/decision/query/verify/complete/trace workflow.
  - `uv run ruff check app tests scripts`; full and focused Pytest suites.
  - Base/profile Compose validation, API image build and `git diff --check`.
  - Real disposable Neo4j repeat rebuild/parity/stale-prune verifier and application-route probes.
  - Wrong-password typed-failure and bounded log-leak probes.
  - Playwright E2E first with six workers, then full serial rerun.
  - Main stack health/readiness and container log checks.

## Reasoning / Decisions

- Decision: PostgreSQL remains the only canonical store; Neo4j owns two rebuildable projections
  keyed by `(projection, graph_id)` and can only be written through explicit owner rebuild.
- Reason: Gate C explicitly requires a verified Neo4j projection, while atomicity, retries, stale
  cleanup, contract validation and fail-visible selection prevent partial or fake graph behavior.
- Alternatives considered: leave the scaffold, multi-transaction delete/recreate, dual writes and
  dynamic Cypher relationship types; rejected in decision 0012/DEC-025.

## Verification

- Tests/checks:
  - Ruff passed; 130 backend tests passed with only the known Starlette/httpx warning.
  - Real proof: relationship 78 nodes/73 edges; hierarchy 45/44; two constraints; zero duplicates;
    injected stale row removed; canonical PostgreSQL counts unchanged; branch 12 nodes; path 2 nodes.
  - Application routes returned 200 for rebuild, both views, search, branch, path and five clusters.
  - Wrong password returned typed 503 `NEO4J_UNAVAILABLE`; log scan found zero Cypher, URI or
    integration credential markers.
  - Base/profile Compose and `git diff --check` passed; Harness story verification/completion passed.
  - Harness detailed trace #12 meets the required high-risk 3/3 tier; audit entropy is `5/100` only
    because product-owner story `US-GV2-ACCEPT` remains intentionally unverified.
  - Playwright parallel run: 25 pass, 6 auth-only skip, 5 dev-server timeouts. Full serial rerun:
    30 pass, 6 auth-only skip.
  - Final main runtime: health `ok`; readiness `ready`, graph valid at 45 nodes/32 edges.
- Result: Neo4j projection story is complete. Gate C remains open for Meilisearch/pgvector and
  deployment-owned operations; the overall goal remains active.

## Known Issues

- The configured OpenAI credential is still rejected, so real chat/product-owner acceptance cannot
  complete without a replacement secret outside source control.
- Projection freshness is explicit; no durable outbox-driven automatic Neo4j sync exists yet.
- Production Neo4j TLS/HA/backups/capacity and secret rotation remain operator responsibilities.
- The initial 512 MiB disposable Neo4j tmpfs exhausted transaction-log preallocation and became
  read-only; 1536 MiB passed. This affected no canonical or persistent product data.
- Root filesystem is 96% used with about 2.6 GiB free. One unused dangling 2.6 GiB rebuildable image
  was removed before pulling Neo4j; no volume or product data was deleted.

## Next Agent Notes

- Continue from: define Meilisearch/pgvector rebuild and parity contracts while waiting for the
  replacement OpenAI credential and product-owner walkthrough.
- Watch out for: do not start Discord Gate D until completion gates pass; do not put credentials in
  the repository/AI logs; do not touch `smart_exam_*`.
- Suggested next command: `scripts/bootstrap-harness.sh && scripts/bin/harness-cli query matrix --active --summary`.
