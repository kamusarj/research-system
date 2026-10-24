# Validation

## Acceptance criteria

1. `_document_chunks` no longer slices mid-word on a "word boundary" legible input;
   overlap defaults to 200 chars and never exceeds `size // 2`; the first chunk is
   the title + summary.
2. `POST /api/v1/search/hybrid` returns HTTP 404 with `FEATURE_DISABLED` when
   `search_hybrid_enabled=false`, and returns the `ResearchList` shape with fused
   results when enabled; `/search` and `/search/semantic` continue to pass.
3. `PgvectorProjection.search` returns at most `limit` research ids, excludes any
   chunk above `search_semantic_max_distance`, and applies MMR selection
   (order differs from naive `min(distance)` on a deliberately duplicated-chunk
   fixture), with shape contract intact.
4. `graph_chat.build_scope_context` for `document` scope, when pgvector is
   enabled, passes top-k nearest chunks (bounded by
   `chat_document_scope_top_k_passages`, truncated to
   `chat_document_scope_passage_chars`) instead of the first `12_000` chars,
   and falls back to first-N when pgvector is disabled or no chunks exist.
5. The five env-only settings exist on `Settings` with the defaults in the design
   doc; every prior search test still passes (with adjusted count assertions where
   overlap increases chunk counts).
6. `ruff check` and `ruff format --check` are clean. Backend pytest suite passes
   at or above its current 256-test count; frontend `eslint`, `tsc --noEmit` and
   the existing unit tests pass unchanged.

## Test commands

```bash
cd apps/api && ruff check app tests && ruff format --check app tests
cd apps/api && uv run pytest -q
cd apps/web && npm run lint && npx tsc --noEmit && npm run test -- --run
```

## Smoke commands (runtime, requires Docker up on 18000/13000)

```bash
API=18000
# Hybrid feature disabled by default → 404:
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:$API/api/v1/search/hybrid \
  -H 'Content-Type: application/json' -d '{"query":"retrieval","limit":5}'
# Rebuild pgvector projection so overlap chunks take effect:
curl -s -X POST http://localhost:$API/api/v1/search/rebuild \
  -H 'Content-Type: application/json' -d '{"projections":["pgvector"]}'
# Re-enable hybrid at runtime via env (restart) then:
curl -s -X POST http://localhost:$API/api/v1/search/hybrid \
  -H 'Content-Type: application/json' -d '{"query":"retrieval","limit":5}'
```

## Evidence quality tier

- Backend pytest summary is required for completion.
- One runtime hybrid smoke (or a recorded reason it could not run) is required
  for the "runtime verified" claim.
- DEC-021 durable record exists before `story complete`.