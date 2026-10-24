from __future__ import annotations

import json

from sqlalchemy import func, select, text

from app.db import SessionLocal
from app.models import ResearchItem, SearchVectorProjection
from app.services.search_projection import (
    MeilisearchProjectionClient,
    PgvectorProjection,
    build_search_documents,
    embedding_client_from_settings,
    hydrate_ranked_research,
    rebuild_search_projections,
)


def canonical_counts(db) -> tuple[int, int]:
    return (
        db.scalar(select(func.count()).select_from(ResearchItem)) or 0,
        db.scalar(
            select(func.count())
            .select_from(ResearchItem)
            .where(ResearchItem.status == "approved")
        )
        or 0,
    )


def main() -> None:
    meilisearch = MeilisearchProjectionClient.from_settings()
    embeddings = embedding_client_from_settings()
    with SessionLocal() as db:
        canonical_before = canonical_counts(db)
        documents = build_search_documents(db)
        if not documents:
            raise RuntimeError("Runtime proof requires at least one approved research item")

        first = rebuild_search_projections(
            db,
            ["meilisearch", "pgvector"],
            meilisearch_factory=lambda: meilisearch,
            embedding_factory=lambda: embeddings,
        )
        second = rebuild_search_projections(
            db,
            ["meilisearch", "pgvector"],
            meilisearch_factory=lambda: meilisearch,
            embedding_factory=lambda: embeddings,
        )
        if first != second:
            raise RuntimeError("Repeated search projection counts do not match")

        with meilisearch._client() as client:
            response = meilisearch._request(
                client,
                "POST",
                f"/indexes/{meilisearch.index}/documents",
                json=[{"id": "stale-runtime-proof", "title": "stale runtime proof"}],
            )
            assert response is not None
            meilisearch._wait_task(client, response)

        seed = db.scalar(select(SearchVectorProjection).limit(1))
        if seed is None:
            raise RuntimeError("pgvector projection did not create any chunks")
        db.execute(
            text(
                """
                INSERT INTO search_vector_projections (
                  id, research_id, chunk_index, content, content_hash, embedding,
                  provider, model, source_updated_at, sync_id, created_at, updated_at
                )
                SELECT
                  'stale-runtime-proof', research_id, 2147483647, content, content_hash,
                  embedding, provider, model, source_updated_at, 'stale-runtime-proof',
                  now(), now()
                FROM search_vector_projections
                LIMIT 1
                """
            )
        )
        db.commit()

        third = rebuild_search_projections(
            db,
            ["meilisearch", "pgvector"],
            meilisearch_factory=lambda: meilisearch,
            embedding_factory=lambda: embeddings,
        )
        if third != first:
            raise RuntimeError("Stale-prune search projection counts do not match")

        meili_ids, meili_total = meilisearch.search(
            query=documents[0].title,
            page=1,
            page_size=20,
            type_filter=None,
            collection_method=None,
            tag=None,
        )
        if not meili_ids or not hydrate_ranked_research(db, meili_ids):
            raise RuntimeError("Meilisearch did not return canonical approved research")

        semantic_ids = PgvectorProjection(embeddings).search(db, "research knowledge", 20)
        if not semantic_ids or not hydrate_ranked_research(db, semantic_ids):
            raise RuntimeError("pgvector did not return canonical approved research")

        vector_chunks = (
            db.scalar(select(func.count()).select_from(SearchVectorProjection)) or 0
        )
        vector_documents = (
            db.scalar(
                select(func.count(func.distinct(SearchVectorProjection.research_id)))
            )
            or 0
        )
        dimensions = db.scalar(
            text("SELECT min(vector_dims(embedding)) FROM search_vector_projections")
        )
        extension_version = db.scalar(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        )
        hnsw_indexes = db.scalar(
            text(
                """
                SELECT count(*)
                FROM pg_indexes
                WHERE tablename = 'search_vector_projections'
                  AND indexdef ILIKE '% USING hnsw %'
                """
            )
        )
        stale_vectors = db.scalar(
            select(func.count())
            .select_from(SearchVectorProjection)
            .where(SearchVectorProjection.id == "stale-runtime-proof")
        )
        canonical_after = canonical_counts(db)

    with meilisearch._client() as client:
        stale_response = meilisearch._request(
            client,
            "GET",
            f"/indexes/{meilisearch.index}/documents/stale-runtime-proof",
            allow_not_found=True,
        )

    if stale_response is not None or stale_vectors:
        raise RuntimeError("Search projections contain stale rows")
    if canonical_before != canonical_after:
        raise RuntimeError("Canonical PostgreSQL counts changed during projection rebuild")
    if meili_total > first["meilisearch"]["projected"]:
        raise RuntimeError("Meilisearch returned an invalid total")
    if vector_documents != canonical_before[1] or dimensions != 1024:
        raise RuntimeError("pgvector projection parity or dimensions are invalid")
    if not extension_version or hnsw_indexes != 1:
        raise RuntimeError("pgvector extension or HNSW index is missing")

    print(
        "SEARCH_PROJECTIONS_OK",
        json.dumps(
            {
                "canonical_research": canonical_before[0],
                "approved_documents": canonical_before[1],
                "meilisearch_documents": first["meilisearch"]["projected"],
                "meilisearch_read_hits": len(meili_ids),
                "vector_documents": vector_documents,
                "vector_chunks": vector_chunks,
                "vector_dimensions": dimensions,
                "semantic_read_hits": len(semantic_ids),
                "pgvector_extension": extension_version,
                "hnsw_indexes": hnsw_indexes,
                "stale_rows": 0,
                "canonical_unchanged": True,
            },
            sort_keys=True,
        ),
    )


if __name__ == "__main__":
    main()
