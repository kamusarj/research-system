# 0013 Atomic Search and Vector Projections

Date: 2026-07-21

## Status

Accepted

## Context

Gate C requires Meilisearch and pgvector to be verified as rebuildable projections. Current search
reads PostgreSQL directly, semantic search is lexical fallback, the base PostgreSQL image lacks the
vector extension, and legacy enrichment vectors are SHA-derived JSON arrays rather than semantic
embeddings. External index availability must not become a condition for canonical research writes.

## Decision

Keep PostgreSQL ResearchItem rows as the only search authority. Build Meilisearch through a fully
configured staging index followed by atomic live/staging swap. Build a dedicated
`search_vector_projections` table from bounded approved-research chunks using real 1024-dimensional
Mistral embeddings and pgvector cosine distance. Do not migrate or query the legacy hash-derived
`embedding_chunks` values.

Provider selection is explicit and independent for lexical and semantic search. PostgreSQL/lexical
fallback remains the local default; selecting Meilisearch or pgvector must fail visibly rather than
silently query a different provider. Search results are hydrated from current canonical PostgreSQL
rows in projection rank order. Rebuild is owner-only, repeatable and count-audited.

## Alternatives Considered

1. Label the current lexical endpoint and JSON arrays as projection proof. Rejected because this
   would overstate semantic behavior.
2. Make Meilisearch documents authoritative responses. Rejected because external staleness could
   overwrite canonical lifecycle/content semantics.
3. Rebuild the live Meilisearch index in place. Rejected because partial settings/documents would be
   user-visible.
4. Synchronously dual-write on publication. Rejected because external failure would couple to the
   canonical transaction and retry ordering.
5. Use Meilisearch vectors only. Rejected because pgvector is part of the accepted architecture and
   keeps semantic projection data transactionally adjacent to PostgreSQL.

## Consequences

Positive:

- Lexical and semantic projections can be independently rebuilt, validated and rolled back to
  existing PostgreSQL behavior without changing frontend routes.
- Real query/document embeddings replace fake semantic claims for the pgvector path.
- Atomic service-local replacement prevents readers from observing partial projection snapshots.

Tradeoffs:

- Multi-projection rebuild is convergent, not a distributed transaction; retries reconcile a partial
  cross-service failure.
- Mistral embedding availability/cost is required only for pgvector rebuild/query when selected.
- The database image changes within PostgreSQL major 16 and requires a logical backup/recreate proof.
- Explicit rebuild freshness remains until an outbox consumer is separately justified.

## Follow-Up

- Measure real-corpus relevance/latency before tuning HNSW or replacing the Mistral embedding model.
- Add durable outbox-driven refresh only when accepted freshness objectives exist.
- Production deployment owns TLS, API-key rotation, snapshots/backups, capacity and network policy.
