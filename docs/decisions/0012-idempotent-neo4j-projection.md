# 0012 Idempotent Neo4j Projection

Date: 2026-07-21

## Status

Accepted

## Context

Gate C requires Neo4j to be verified as a rebuildable projection, but the current selected provider
is only an explicit 501 scaffold. PostgreSQL must remain canonical, the public graph contract must
stay stable, and a failed or retried external write must not create duplicates or expose a partial
replacement graph.

## Decision

Project both relationship and hierarchy views into Neo4j using composite `(projection, graph_id)`
identities, uniqueness constraints and parameterized batched `UNWIND`/`MERGE` statements. Perform
both view replacements and stale-row pruning in one managed write transaction. Validate every
payload with the existing Pydantic graph schemas before writing and after reading.

Neo4j remains read-only from the product's perspective: only the owner-only explicit rebuild may
write projection-labeled rows. PostgreSQL remains the source of truth and there is no implicit
fallback. External service/auth/payload failures return bounded, secret-free typed errors.

## Alternatives Considered

1. Keep the scaffold and document Neo4j as optional. Rejected because Gate C explicitly requires
   verified projection adapters.
2. Delete/recreate the projection in separate transactions. Rejected because failure can expose an
   empty or partial graph.
3. Dual-write canonical mutations to PostgreSQL and Neo4j. Rejected because it creates a second
   write path and couples publication availability to an external projection.
4. Store each domain relationship as a dynamic Cypher relationship type. Rejected because the
   fixed projection relationship plus validated type property is safer to parameterize and rebuild.

## Consequences

Positive:

- Rebuilds are repeatable, duplicate-safe and rollback atomically on failure.
- The existing API/UI can select Neo4j without contract changes.
- Relationship and hierarchy parity can be measured from one PostgreSQL source snapshot.

Tradeoffs:

- Projection freshness is explicit rather than automatic until an outbox-driven sync story exists.
- Full replacement transactions are appropriate for the current bounded corpus but need load/capacity
  testing before very large graphs.
- Production Neo4j TLS, clustering, backup and credentials remain deployment responsibilities.

## Follow-Up

- Verify Meilisearch and pgvector with the same canonical/rebuild/parity rules.
- Consider an idempotent outbox consumer only after explicit rebuild behavior is accepted.
