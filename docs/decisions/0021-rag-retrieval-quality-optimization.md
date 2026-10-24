# 0021 RAG retrieval quality optimization

Date: 2026-07-31

## Status

Accepted

## Context

DEC-026 locked pgvector `vector(1024)` Mistral `mistral-embed` semantic search plus
atomic Meilisearch lexical projection; DEC-019/DEC-029 locked governed chat provider
behavior; DEC-025 locked Neo4j as a rebuildable projection. The retrieval layer
itself, however, has three measurable weaknesses discovered during intake #32:

1. `search_projection._document_chunks` slices text with `text[start:start+size]`
   and no overlap, so a concept split across a chunk boundary loses recall and a
   word cut mid-token produces noise.
2. `/search` (lexical) and `/search/semantic` (vector) are two disconnected routes
   with no fusion; the user must pick one and miss the other's signal.
3. `PgvectorProjection.search` returns `min(distance)` per `research_id` with no
   diversity or relevance cutoff, so one near document can dominate all slots and
   far chunks (>0.7 cosine distance) still rank.
4. `graph_chat.build_scope_context` feeds the document-scoped chat the first
   `12_000` characters of `research.content`; for long documents the answerable
   passage may be later and never reach the provider.

## Decision

Optimize the existing RAG retrieval inside the locked architecture, without
changing the Mistral embedding model or `embedding_chunks`/`SearchVectorProjection`
schema:

- **A. Chunk overlap + word boundary**: `_document_chunks` splits on word
  whitespace so each chunk ends and starts on a word, adds
  `search_embedding_chunk_overlap_chars` (default 200) of overlap, and keeps a
  sentinel title+summary first chunk. Bound by `search_embedding_chunk_min_chars`
  (default 100) and the existing `max_per_item` cap.
- **B. Hybrid search endpoint (additive)**: add `POST /api/v1/search/hybrid` that
  fuses the existing pgvector semantic and Meilisearch/Postgres lexical lists by
  Reciprocal Rank Fusion (`score = sum(1/(k + rank))`, `k = 60`). Gated by
  `search_hybrid_enabled` (default false), returns the same `ResearchList` hydrating
  canonical PostgreSQL rows; `/search` and `/search/semantic` are unchanged.
- **C. MMR + threshold**: `PgvectorProjection.search` applies Maximal Marginal
  Relevance (`search_mmr_lambda`, default 0.5) over the per-chunk distance with the
  query vector, then returns the canonical `research_id` order; chunks above
  `search_semantic_max_distance` (default 0.7) are excluded before ranking.
- **D. Chat document-scope passage retrieval**: `build_scope_context` for
  `document` scope retrieves `chat_document_scope_top_k_passages` (default 6)
  nearest `SearchVectorProjection` chunks to the current user message, each
  trimmed to `chat_document_scope_passage_chars` (default 1500); it falls back to
  the first `chat_max_context_chars // 2` characters when pgvector is disabled or
  no chunks exist, preserving prior behavior.
- **E. Settings + tests**: five env-only settings added to `Settings`; four unit
  tests added covering chunk overlap/word boundary, RRF fusion, MMR diversity,
  semantic distance cutoff, and document-scope passage retrieval; existing tests
  are only updated when their chunk-count assertions need to widen.

## Alternatives Considered

1. Replace `mistral-embed` with a newer or multimodal embedding model. Rejected: it
   breaks DEC-026's locked `vector(1024)` contract and forces a full projection
   rebuild plus dimension migration.
2. Integrate LightRAG. Rejected by DEC-034: its own vector/graph storage duplicates
   pgvector/Neo4j and bypasses governed change sets.
3. Add a cross-encoder reranker (e.g. Cohere/Mistral rerank). Rejected: introduces a
   new external provider contract outside the harness-locked Mistral embed path.
4. Keep first-N-chars chat context. Rejected: long documents lose the relevant
   tail silently, the precise weakness intake #32 must close.

## Consequences

Positive:

- Retrieval recall and precision improve with no schema migration, no new provider
  contract, and no change to `/search`/`/search/semantic` contracts.
- The chat document scope finally reads the passage the user asked about, not the
  document header.
- All five optimizations are settings-gated and reversible.

Tradeoffs:

- Chunk overlap raises `embedding_chunks`/`SearchVectorProjection` row counts by
  up to ~25% (one overlap chunk per boundary) and increases Mistral embedding cost
  on rebuild; it is bounded by the existing per-item cap and owner-initiated rebuild.
- MMR adds linear-time selection over the top-N chunk candidates; cost is bounded
  by `search_max_results` and the projection size.
- Hybrid search adds one endpoint and one settings toggle; disabled by default.
- Runtime rebuild via `POST /api/v1/search/rebuild` is required for chunk-overlap
  rows to take effect; old rows keep working until rebuild.

## Follow-Up

- Operationally rebuild the pgvector projection after deploying this change.
- If fusion quality reviews well, consider flipping `search_hybrid_enabled` to true
  by default in a separate accepted decision.
- Trend/failed-search signals (DEC-009) remain follow-up out of scope here.