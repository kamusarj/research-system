# Design

## Architecture alignment

Per DEC-026, PostgreSQL `embedding_chunks`/`SearchVectorProjection` rows remain the
only durable chunk store. Per DEC-025, Neo4j stays a rebuildable projection. Per
DEC-019/029, chat remains governed (read/propose-only). Every change below is
inside adapters/services and adds no migration.

## A. Chunk overlap + word boundary

File: `apps/api/app/services/search_projection.py::_document_chunks`.

Replace the fixed-window slice with:

```python
def _split_on_word_boundaries(text: str, size: int, overlap: int, min_chars: int) -> list[str]:
    if len(text) <= size:
        return [text] if text.strip() else []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start + min_chars:
                end = boundary
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1) if overlap else end
    return [c for c in chunks if c]
```

Compose chunks as: first chunk = `title + "\n\n" + summary` (boost the title); the
rest iterate `_split_on_word_boundaries` over `content` and concatenate up to the
existing limit (default `search_embedding_max_chunks_per_item = 32`).

Bounds:
- `size = max(256, min(settings.search_embedding_chunk_chars, 16_000))` (existing).
- `overlap = max(0, min(settings.search_embedding_chunk_overlap_chars, size // 2))`.
- `min_chars = max(1, min(settings.search_embedding_chunk_min_chars, size))`.

## B. Hybrid search endpoint (additive)

File: `apps/api/app/api/search.py`, `apps/api/app/schemas/search.py`.

```python
class HybridSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2_000)
    limit: int = Field(default=20, ge=1, le=100)
    type_filter: str | None = Field(default=None, max_length=40)
    collection_method: str | None = Field(default=None, max_length=30)
    tag: str | None = Field(default=None, max_length=60)


@router.post("/hybrid", response_model=ResearchList)
def hybrid_search(payload: HybridSearchRequest, db: Session = Depends(get_db)) -> ResearchList:
    if not settings.search_hybrid_enabled:
        raise HTTPException(status_code=404, detail={"code": "FEATURE_DISABLED"})
    ...
```

RRF fusion:

```python
def reciprocal_rank_fusion(rank_lists: list[list[str]], k: int = 60) -> list[str]:
    scores: dict[str, float] = {}
    for ranked in rank_lists:
        for rank, item_id in enumerate(ranked):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
    return [item_id for item_id, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))]
```

Behaviour:

1. When `search_data_provider == "meilisearch"`, call lexical through the existing
   `MeilisearchProjectionClient.search(...)` and pull `limit` ids.
2. When pgvector is selected (`vector_data_provider == "pgvector"`), call
   `PgvectorProjection.search` for `limit` semantic ids.
3. Otherwise fall back: lexical via local Postgres `search_statement`, semantic
   via local Postgres (no vectors).
4. Fuse with RRF; hydrate via existing `hydrate_ranked_research`.

`hybrid_router` and `semantic_search` are unchanged.

## C. MMR + threshold in semantic search

File: `apps/api/app/services/search_projection.py::PgvectorProjection.search`.

```python
def search(self, db: Session, query: str, limit: int) -> list[str]:
    vector = self.embedding_client.embed([query])[0]
    max_distance = settings.search_semantic_max_distance
    lambda_mmr = settings.search_mmr_lambda
    # fetch top-N chunks (limit * 3, capped by search_max_results)
    rows = db.execute(
        select(
            SearchVectorProjection.research_id,
            SearchVectorProjection.embedding.op("<=>", return_type=Float())(vector).label("distance"),
        ).order_by("distance").limit(min(max(limit * 3, 10), settings.search_max_results))
    ).all()
    # cutoff
    rows = [r for r in rows if r.distance <= max_distance]
    # MMR over per-chunk candidates
    selected = mmr_select(rows, lambda_mmr, query_vector=vector, limit=limit)
    # final research_id order, uniqueness preserved
    seen = set()
    out = []
    for sid in selected:
        rid = sid.research_id
        if rid in seen:
            continue
        out.append(rid); seen.add(rid)
    return out[:limit]
```

MMR scoring: for each unselected candidate `c`,
`score(c) = lambda_mmr * sim(query, c) - (1 - lambda_mmr) * max(sim(c, s) for s in selected)`.
`sim = 1 - distance`. Cosine distance is what pgvector's `<=>` already returns.
We don't re-embed; `query_vector` is the same vector used for the cutoff.

Fall-back: if pgvector selection is unavailable (`SQLAlchemyError`), existing
`PGVECTOR_UNAVAILABLE` typed error remains.

## D. Chat document-scope passage retrieval

File: `apps/api/app/services/graph_chat.py::build_scope_context`.

Replace the document branch's:

```python
document_text_limit = min(12_000, max(1_000, settings.chat_max_context_chars // 2))
document_text = (research.content if research else "") or ""
```

with:

```python
passages = _retrieve_document_passages(db, session, research)
# returns list[(chunk_id, content)], already deduplicated and bounded
```

Implementation:

```python
def _retrieve_document_passages(db, session, research) -> list[dict[str, Any]]:
    if not research or settings.vector_data_provider != "pgvector":
        # preserve prior behaviour when pgvector not enabled
        limit = min(12_000, max(1_000, settings.chat_max_context_chars // 2))
        text = (research.content if research else "") or ""
        return [{"id": None, "excerpt": text[:limit], "truncated": len(text) > limit}]
    # Pull last user message as the query; fall back to research title.
    query = _last_user_message(db, session.id) or research.title
    rows = PgvectorProjection(MistralEmbeddingClient.from_settings()).search_chunks(
        db, query=query, research_id=research.id,
        limit=settings.chat_document_scope_top_k_passages,
    )
    per = settings.chat_document_scope_passage_chars
    return [{"id": r.chunk_id, "excerpt": r.content[:per]} for r in rows] or \
        [{"id": None, "excerpt": research.content[:12_000], "truncated": False}]
```

Add `PgvectorProjection.search_chunks(db, query, research_id, limit)` returning
`list[SimpleNamespace(chunk_id, content, distance)]` filtered to that research_id.
The chat redact-before-send already exists (`redact_cloud_text` on `context_text`),
so this path holds provenance unchanged.

## E. Settings + tests

`apps/api/app/core/config.py` adds:

```python
search_embedding_chunk_overlap_chars: int = 200
search_embedding_chunk_min_chars: int = 100
search_hybrid_enabled: bool = False
search_mmr_lambda: float = 0.5
search_semantic_max_distance: float = 0.7
chat_document_scope_top_k_passages: int = 6
chat_document_scope_passage_chars: int = 1_500
```

All env-only and reversable.

## Risk review

- **Public contracts**: `/search` and `/search/semantic` unchanged. `/search/hybrid`
  is additive and disabled by default, returning the same `ResearchList`.
- **Existing behavior**: chunking counts change; only `test_pgvector_projection_*`
  and tests asserting `chunks >= 2` remain valid.
- **Weak proof**: adds exhaustive unit tests for the four algorithms.
- **Multi-domain**: search + chat both touched; both are covered by focused tests.