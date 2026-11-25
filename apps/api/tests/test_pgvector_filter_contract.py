"""Exercise real PostgreSQL filtering before ranking/limit on a disposable migrated DB."""

import hashlib
import os
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ResearchItem, SearchVectorProjection, Tag, utcnow
from app.services.search_projection import PgvectorProjection


@pytest.mark.parametrize("filter_name", ["type", "collection", "tag", "combined"])
def test_pgvector_metadata_filters_precede_limit(monkeypatch, filter_name):
    value = os.environ.get("RESEARCH_LEASE_TEST_DATABASE_URL")
    if not value:
        pytest.skip("Requires migrated disposable PostgreSQL baa_ci_* database")
    url = make_url(value)
    if url.get_backend_name() != "postgresql" or not (url.database or "").startswith("baa_ci_"):
        pytest.fail("Search filter test requires a disposable baa_ci_* PostgreSQL database")

    identity = uuid.uuid4().hex
    tag_name = f"rag-{identity}"

    class Embedding:
        provider = "audit-filter"
        model = identity

        def embed_query(self, _query):
            return [1.0] + [0.0] * 1023

    engine = create_engine(url)
    try:
        with Session(engine) as db:
            rag = Tag(name=tag_name, display_name=tag_name)
            other = Tag(name=f"other-{identity}", display_name="Other")
            items = {}
            for index, (name, kind, collection, tags, status) in enumerate(
                (
                    ("good", "reference", "upload", [rag], "approved"),
                    ("wrong_type", "internal-research", "upload", [rag], "approved"),
                    ("wrong_collection", "reference", "manual", [rag], "approved"),
                    ("wrong_tag", "reference", "upload", [other], "approved"),
                    ("draft", "reference", "upload", [rag], "draft"),
                )
            ):
                item = ResearchItem(
                    title=f"Synthetic {name}",
                    content="Synthetic evidence",
                    type=kind,
                    collection_method=collection,
                    status=status,
                    tags=tags,
                    approved_at=utcnow(),
                )
                db.add(item)
                db.flush()
                items[name] = item.id
                vector = [0.9, 0.1] + [0.0] * 1022 if name == "good" else [1.0] + [0.0] * 1023
                db.add(
                    SearchVectorProjection(
                        id=f"{identity}-{index}",
                        research_id=item.id,
                        chunk_index=0,
                        content="Synthetic evidence",
                        content_hash=hashlib.sha256(name.encode()).hexdigest(),
                        embedding=vector,
                        provider=Embedding.provider,
                        model=Embedding.model,
                        source_updated_at=utcnow(),
                        sync_id=identity,
                    )
                )
            db.flush()
            monkeypatch.setattr(settings, "search_mmr_lambda", 1.0)
            monkeypatch.setattr(settings, "search_semantic_max_distance", 0.5)
            filters = {
                "type": {"type_filter": "reference"},
                "collection": {"collection_method": "upload"},
                "tag": {"tag": tag_name},
                "combined": {
                    "type_filter": "reference",
                    "collection_method": "upload",
                    "tag": tag_name,
                },
            }[filter_name]
            expected = {
                "type": {"good", "wrong_collection", "wrong_tag"},
                "collection": {"good", "wrong_type", "wrong_tag"},
                "tag": {"good", "wrong_type", "wrong_collection"},
                "combined": {"good"},
            }[filter_name]
            found = PgvectorProjection(Embedding()).search(
                db, "synthetic", 1 if filter_name == "combined" else 10, **filters
            )
            assert set(found) == {items[name] for name in expected}
            db.rollback()
    finally:
        engine.dispose()
