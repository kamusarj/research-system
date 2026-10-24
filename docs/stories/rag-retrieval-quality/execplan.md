# Exec Plan

## Lane

High-risk. Flags: PublicContracts, ExistingBehavior, WeakProof, MultiDomain.
Intake #32.

## Order

1. Settings (config.py) — add 7 env-only knobs (cheap, isolated).
2. `search_projection.py::_document_chunks` — overlap + word boundary (A).
3. `search_projection.py::PgvectorProjection.search` — cutoff + MMR (C).
4. `search_projection.py::PgvectorProjection.search_chunks` — research-scoped
   chunk retrieval used by chat (D).
5. `api/search.py` + `schemas/search.py` — `POST /api/v1/search/hybrid` (B).
6. `services/graph_chat.py::build_scope_context` — document-scope passages (D).
7. Tests (E):
   - update `test_pgvector_projection_rebuild_is_repeatable_and_prunes_stale_rows`
     (chunk count changes).
   - add `test_chunk_split_uses_word_boundary_and_overlap`.
   - add `test_reciprocal_rank_fusion_orders_by_score`.
   - add `test_pgvector_search_applies_mmr_and_distance_cutoff`.
   - add `test_hybrid_search_fuses_lexical_and_semantic`.
   - add `test_document_scope_chat_uses_passage_retrieval`.
8. ruff lint/format + full pytest backend + frontend lint/typecheck.
9. Runtime verification (separate sequence): start local Docker on
   `API_PORT=18000 FRONTEND_PORT=13000`, rebuild pgvector projection, smoke
   `/api/v1/search/hybrid` and one document-scoped chat turn.

## Verification evidence to collect for trace

- `ruff check` and `ruff format --check` exit codes.
- `pytest apps/api/tests -q` summary (pass/total).
- Hybrid endpoint smoke (HTTP 404 when disabled; HTTP 200 when enabled).
- `git status --short` after edits.
- Result of runtime rebuild if attempted.

## Rollback

Each step is a git diff hunk; `git stash`/`git checkout -- <file>` reverts in
isolation. No migration is added, so no downgrade is needed. Old vector rows
keep working until an operator rebuilds; chunk-offset rows are deterministic
per rebuild, so re-running `POST /api/v1/search/rebuild` with prior code would
simply revert the chunk layout.