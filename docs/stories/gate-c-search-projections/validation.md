# Validation

## Proof Strategy

Prove both projections derive only from approved PostgreSQL research, repeat rebuilds without
duplicates, remove controlled stale rows, return canonical hydrated responses through the existing
contracts, and fail visibly without leaking queries, documents, vectors, URLs or credentials.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Projection DTO/chunk/vector validation, Meili filter escaping, task polling, response parsing, typed errors. |
| Integration | Rebuild repeat/parity/stale prune, selected-provider lexical/semantic/suggest behavior, canonical hydration, owner policy. |
| E2E | Existing search page and primary workspace hydration remain unchanged. |
| Platform | SQLite migration parity, real PostgreSQL extension/type/index, Meilisearch atomic swap, image/profile/secret config. |
| Performance | Bounded source text/chunks/batches/results/tasks; Meili index swap; pgvector cosine HNSW. |
| Logs/Audit | Count-only rebuild log and safe error envelopes; no query/body/vector/URI/credential leakage. |

## Fixtures

- Approved and non-approved research with tags, authors and canonical timestamps.
- Fake Meilisearch HTTP/task boundary with a stale live index.
- Fake 1024-dimensional embedding client plus malformed count/dimension/non-finite responses.
- Disposable real Meilisearch and pgvector-enabled PostgreSQL/application runtime.

## Commands

```text
cd apps/api && uv run ruff check app tests scripts
cd apps/api && uv run python -m pytest -q
make verify-migrations
docker compose config --quiet
docker compose --profile search config --quiet
docker compose build api
scripts/bin/harness-cli story verify US-GATEC-SEARCH-PROJECTIONS
```

## Acceptance Evidence

- Ruff and all 141 backend tests pass; the focused projection suite has 11 cases.
- SQLite migration upgrade/check/downgrade/upgrade passes at `c5a8e2f4b901`; base and optional-search
  Compose configurations validate.
- The main PostgreSQL 16 volume was logically backed up before its image changed, then upgraded in
  place to pgvector 0.8.5 without changing the 8 canonical / 3 approved research counts.
- A disposable real Meilisearch 1.37 server plus the live pgvector PostgreSQL and real
  `mistral-embed` endpoint passed three rebuilds, including injected stale rows. Final parity was 3
  Meilisearch documents, 3 vector documents / 9 chunks, 1024 dimensions, one HNSW index, zero stale
  rows and unchanged canonical counts. Lexical and semantic reads each returned canonical approved
  research.
- The disposable Meilisearch container and rebuildable proof volume were removed after verification;
  the internal-only profile and migration remain configured.
- The managed-secret Compose overlay starts Meilisearch successfully with its master key mounted as
  a Docker secret; the proof container and projection volume were removed afterward.
- Frontend ESLint, TypeScript and all 28 Vitest tests pass; 30 Playwright cases pass across desktop,
  tablet and mobile (six auth-only cases skipped because local auth is disabled).
