# Design

## Domain Model

`SearchDocument` is a validated projection of one approved `ResearchItem`, including stable ID,
display ID, title, summary/content, type, collection method, authors, normalized/display tags,
source URL and canonical timestamps. PostgreSQL remains the only authority for lifecycle and full
response serialization.

`SearchVectorProjection` is a rebuildable chunk row keyed by stable `(research_id, chunk_index)`.
It stores a bounded source excerpt, content hash, embedding provider/model, canonical update time and
a 1024-dimensional vector. Legacy `EmbeddingChunk` JSON vectors remain readable historical
enrichment artifacts but are not queried by the pgvector adapter.

## Application Flow

1. An owner invokes `POST /api/v1/search/rebuild` for one or both projections.
2. The service reads and validates one approved PostgreSQL snapshot.
3. Meilisearch rebuild creates a clean staging index, applies explicit searchable/filterable/sortable
   settings, adds documents in bounded batches, waits for every asynchronous task, validates count,
   creates an empty live index when needed, atomically swaps live/staging, then deletes the old data.
4. pgvector rebuild chunks bounded title/summary/content input, obtains real Mistral embeddings in
   bounded batches, validates count/dimension/finite numbers, and atomically upserts/prunes rows.
5. The response reports per-projection source/projected counts and provider/model metadata only.
6. Selected-provider reads return stable result IDs, then hydrate current canonical ResearchItem
   responses from PostgreSQL in projection rank order.

Meilisearch staging and pgvector replacement are independently atomic. There is deliberately no
claim of a distributed transaction: a partial multi-projection failure remains visible and a repeat
rebuild converges both projections.

## Interface Contract

- Existing `GET /api/v1/search`, `GET /api/v1/search/suggest`,
  `POST /api/v1/search/semantic` and related-research response shapes remain unchanged.
- `POST /api/v1/search/rebuild` is owner-only. Its bounded request selects `meilisearch`,
  `pgvector`, or both; its response contains no document text, vectors, URLs or secrets.
- `SEARCH_DATA_PROVIDER=meilisearch` routes lexical search/suggest through the external index.
- `VECTOR_DATA_PROVIDER=pgvector` embeds the query through the configured Mistral model and performs
  cosine-distance retrieval over approved projection rows.
- Provider configuration/auth/connectivity/task/schema/parity failures are typed HTTP 503 errors.
  Invalid request input remains HTTP 422. There is no implicit PostgreSQL fallback.

## Data Model

- Enable PostgreSQL extension `vector` when running on PostgreSQL.
- Add `search_vector_projections` with a `vector(1024)` embedding on PostgreSQL and a JSON-compatible
  test representation on SQLite.
- Add a unique `(research_id, chunk_index)` constraint and a cosine HNSW index on PostgreSQL.
- Keep an FK to canonical research with cascade delete; rebuild still prunes stale projection rows.
- Upgrade the Compose database image within PostgreSQL major 16 to the digest-pinned official
  pgvector image. Preserve the existing named volume and take a pre-recreate logical dump.

## UI / Platform Impact

No frontend contract change. Meilisearch is an optional internal-only Compose profile with a named
rebuildable data volume. PostgreSQL remains in the base profile but uses a pgvector-enabled image.
API/worker credentials remain server-side and support `/run/secrets` precedence.

## Observability

Rebuild logs include provider, outcome, duration and bounded counts only. Search logs never include
queries, document bodies, vectors, provider URLs or credentials. Meilisearch and Mistral raw client
errors are mapped to stable application codes.

## Alternatives Considered

1. Treat the lexical semantic fallback or legacy SHA-derived JSON arrays as pgvector proof. Rejected
   because neither demonstrates semantic retrieval.
2. Let Meilisearch return full persisted documents as canonical API responses. Rejected because
   stale projection payloads must not override current PostgreSQL state.
3. Delete/rebuild the live Meilisearch index in place. Rejected because readers could observe an
   empty or partially configured index; atomic index swap is available.
4. Dual-write every research mutation synchronously. Rejected because external availability would
   become part of canonical publication and retries could diverge.
5. Use Meilisearch's own vector feature instead of pgvector. Rejected because the accepted target
   architecture explicitly separates lexical Meilisearch and PostgreSQL pgvector projections.
