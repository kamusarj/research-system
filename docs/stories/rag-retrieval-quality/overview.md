# Overview

## Current Behavior

The Research System retrieval layer (locked by DEC-026) is functional but blunt:

- `apps/api/app/services/search_projection.py::_document_chunks` slices text into
  fixed 4000-character windows with no overlap and cuts mid-token, so concepts
  split across a boundary lose recall and noise enters a chunk's start/end.
- `/api/v1/search` (lexical, Meilisearch or Postgres LIKE) and
  `/api/v1/search/semantic` (pgvector cosine) are disconnected routes; the client
  must pick one and miss the other signal.
- `PgvectorProjection.search` returns whichever chunk has the smallest cosine
  distance per `research_id`, with no diversity or relevance cutoff, so one
  near document can dominate every slot and far chunks still rank.
- `graph_chat.build_scope_context` for `scope_type == "document"` feeds the
  provider the first `12_000` characters of `research.content`; for a long
  document the answerable passage may be later and never reach the model.

## Target Behavior

After this story all four weaknesses are closed **without** changing the Mistral
embedding model, the `embedding_chunks`/`SearchVectorProjection` schema, the Neo4j
projection boundary (DEC-025), or governed chat behavior (DEC-019/029):

1. Chunks split on word boundaries with a configurable overlap (default 200 chars)
   and a sentinel title+summary first chunk.
2. New `POST /api/v1/search/hybrid` fuses lexical + semantic candidates via
   Reciprocal Rank Fusion (k=60), gated by `search_hybrid_enabled` (default false);
   `/search` and `/search/semantic` are unchanged.
3. `PgvectorProjection.search` applies MMR (`search_mmr_lambda` default 0.5) over
   per-chunk distance to the query and excludes chunks above
   `search_semantic_max_distance` (default 0.7) before ranking; the returned
   `list[research_id]` shape is unchanged.
4. The chat document scope retrieves `chat_document_scope_top_k_passages` (default
   6) nearest `SearchVectorProjection` chunks to the current user message, each
   trimmed to `chat_document_scope_passage_chars` (default 1500), with first-N
   fallback when pgvector is disabled or no chunks exist.

## Affected Users

- Researchers / owners searching and reviewing research items.
- Researchers/owners using chat against documents and wanting the AI to read the
  passage they actually asked about.

## Affected Product Docs

- `Docs/Research System Implementation Plan.md` Phase 3 (search) and Phase 5
  (AI enrichment / chat scope).
- `apps/api/app/services/search_projection.py`, `app/api/search.py`,
  `app/schemas/search.py`, `app/core/config.py`, `app/services/graph_chat.py`,
  `apps/api/tests/test_search_projections.py`, `apps/api/tests/test_graph_chat.py`.

## Non-Goals

- Replace or augment the Mistral `mistral-embed` / `vector(1024)` contract.
- Add a cross-encoder/external reranker provider.
- Add new schema migrations or change the embeddings table shape.
- Change `/search` or `/search/semantic` response contracts.
- Persist HTTP conditional-GET validators; auto-apply search projections on every
  research change (still owner-initiated rebuild per DEC-026).