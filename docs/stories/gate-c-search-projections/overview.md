# Overview

## Current Behavior

Approved research search is served directly from PostgreSQL. The public semantic-search route keeps
its MVP response contract but performs lexical matching. `embedding_chunks.embedding` contains a
legacy JSON artifact generated during enrichment; it is not a pgvector index and must not be used as
evidence of semantic retrieval quality. No Meilisearch service, atomic search-index rebuild, real
query embedding client or pgvector projection exists.

Gate C in `Docs/Research System Completion Plan.md` explicitly requires Meilisearch and pgvector to
be verified as rebuildable projections while PostgreSQL remains authoritative.

## Target Behavior

An owner can explicitly rebuild either or both search projections from approved PostgreSQL research:

- Meilisearch receives a complete staging index with validated settings/documents, then atomically
  swaps it into the stable live index and removes the old staging data.
- A dedicated PostgreSQL `search_vector_projections` table receives bounded chunks embedded by the
  configured real Mistral embedding endpoint and stored as pgvector `vector(1024)` values. One
  transaction upserts the snapshot and prunes stale rows.

Operators may independently select `postgres`/`meilisearch` for lexical search and
`postgres`/`pgvector` for semantic search. The defaults preserve existing local behavior. An
explicitly selected external provider never falls back silently; missing configuration, invalid
provider data, task failure and parity failure return typed, secret-free errors.

## Affected Users

- Owners rebuilding and validating search projections.
- Researchers/viewers using lexical and semantic discovery.
- Deployment operators configuring pgvector-capable PostgreSQL, Meilisearch and Mistral embedding
  credentials.

## Affected Product Docs

- `Docs/Research System Completion Plan.md`
- `Docs/Research System Architecture Design.md`
- `Docs/Research System Implementation Plan.md`
- `README.md`

## Non-Goals

- Making Meilisearch or vector rows canonical.
- Automatic outbox consumption or a distributed transaction across PostgreSQL and Meilisearch.
- Migrating legacy hash-derived `embedding_chunks` into semantic search.
- Supporting every LLM vendor as an embedding provider in this story.
- Changing frontend result shapes or exposing search credentials to the browser.
