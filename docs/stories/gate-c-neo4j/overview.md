# Overview

## Current Behavior

PostgreSQL is the canonical Research System database and already builds validated relationship and
hierarchy graph responses. `GRAPH_DATA_PROVIDER=neo4j` is only a fail-visible scaffold: it returns
503 when unconfigured and 501 when configured. `POST /api/v1/graph/rebuild` reports PostgreSQL
counts but does not write an external projection.

Gate C in `Docs/Research System Completion Plan.md` requires the Neo4j adapter to be verified as a
rebuildable projection. The accepted graph plans require stable typed keys, idempotent writes,
bounded reads, no silent fallback and no canonical writes from Neo4j.

## Target Behavior

An owner can explicitly rebuild both the relationship and hierarchy projections from one
PostgreSQL snapshot into Neo4j. The rebuild uses constraints plus parameterized, batched `UNWIND`
and `MERGE` statements inside a managed atomic write transaction, then removes stale projection
rows. Repeating the same rebuild produces the same graph without duplicates.

Selecting `GRAPH_DATA_PROVIDER=neo4j` serves the existing validated `{nodes, edges, meta}` contract
from Neo4j with the same query/filter/limit semantics. Missing configuration, authentication,
connectivity and invalid projection payloads fail with typed, secret-free errors; the application
never falls back to PostgreSQL implicitly.

## Affected Users

- Owners operating or rebuilding the graph projection.
- Researchers and viewers reading graph, hierarchy, search and neighbor views.
- Deployment operators configuring an optional Neo4j service and managed credentials.

## Affected Product Docs

- `Docs/Research System Completion Plan.md`
- `Docs/Research System Implementation Plan.md`
- `Docs/Research System Architecture Design.md`
- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`
- `README.md`

## Non-Goals

- Making Neo4j canonical or permitting Neo4j-to-PostgreSQL writes.
- Automatic schema/data migration outside the explicit projection rebuild.
- Adding Meilisearch or pgvector in this story.
- Changing the public graph response shape or Graph Intelligence approval workflow.
- Running Neo4j in the base local Compose profile.
