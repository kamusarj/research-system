# Validation

## Proof Strategy

Prove that Neo4j is a real but non-canonical projection: PostgreSQL produces the full source
snapshot; Neo4j rebuild is atomic, repeatable and removes only stale projection rows; reads remain
bounded and schema-validated; selected-provider failures are explicit. A disposable real server
must match PostgreSQL counts for both views after two rebuilds and after a controlled stale-row
change.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Payload validation/serialization, batching, composite keys, no secret/error leakage. |
| Integration | Relationship/hierarchy rebuild, duplicate-free repeat, stale prune, query filters/root/depth/limits, typed service failure. |
| E2E | Existing graph UI/API contract remains unchanged; no new browser workflow is required. |
| Platform | Base/Neo4j Compose config, API image driver import, internal-only service, real server parity smoke. |
| Performance | Batched `UNWIND`, bounded query limits, one atomic managed write transaction. |
| Logs/Audit | Count-only logs; no payload, URI, password or raw driver exception. |

## Fixtures

- Existing approved ResearchItem/tag/relation projection fixture.
- Seeded approved canonical ontology hierarchy.
- Fake managed driver/transaction for deterministic Cypher and failure tests.
- Disposable Neo4j Community container with integration-only credentials.

## Commands

```text
cd apps/api && uv run ruff check app tests scripts
cd apps/api && uv run python -m pytest -q
docker compose config --quiet
NEO4J_PASSWORD=integration-only-password docker compose --profile neo4j config --quiet
docker compose build api
docker compose run --rm api python scripts/verify_neo4j_projection.py
scripts/bin/harness-cli story verify US-GATEC-NEO4J
```

## Acceptance Evidence

- Ruff and the full API suite pass, including fake-driver contract tests for validation,
  parameterized batching, bounded reads, typed failures and shortest path.
- Repeated real-server proof returned `constraints=2`, `duplicates=0`, unchanged canonical counts,
  relationship parity `78/73`, hierarchy parity `45/44`, a 12-node bounded hierarchy branch and a
  two-node shortest path after an injected stale row was pruned.
- Application-route proof returned HTTP 200 for explicit rebuild, both graph views, search,
  hierarchy branch, shortest path and five bounded clusters while `GRAPH_DATA_PROVIDER=neo4j`.
- A wrong-password application probe returned typed HTTP 503 `NEO4J_UNAVAILABLE` without echoing
  the credential. JSON logs contain provider/duration/count fields only; the raw Neo4j notification
  logger is suppressed because it can emit Cypher text.
- Base and optional-profile Compose render successfully; the optional service is internal-only,
  image-digest pinned and supports separate API/server Docker secret files.
- The first disposable smoke used an undersized 512 MiB tmpfs and Neo4j correctly switched itself
  read-only when transaction-log preallocation exhausted it. Re-running with 1536 MiB passed; no
  PostgreSQL or persistent product data was affected.
