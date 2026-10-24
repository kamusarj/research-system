import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.db import get_db
from app.models import ResearchItem, ResearchRelation, Tag
from app.schemas.research import ResearchList, ResearchRead
from app.schemas.search import (
    HybridSearchRequest,
    SearchRebuildRequest,
    SearchRebuildResponse,
    SemanticSearchRequest,
    reciprocal_rank_fusion,
)
from app.services.projection_state import mark_projection_rebuilt
from app.services.research import get_research_or_404, serialize_research
from app.services.search_projection import (
    MeilisearchProjectionClient,
    PgvectorProjection,
    embedding_client_from_settings,
    hydrate_ranked_research,
    rebuild_search_projections,
)

router = APIRouter(prefix="/search", tags=["search"])
logger = logging.getLogger("research-api.search-projection")


def search_statement(q: str):
    term = f"%{q.lower().strip()}%"
    return (
        select(ResearchItem)
        .options(selectinload(ResearchItem.tags))
        .where(
            ResearchItem.status == "approved",
            or_(
                func.lower(ResearchItem.title).like(term),
                func.lower(func.coalesce(ResearchItem.summary, "")).like(term),
                func.lower(ResearchItem.content).like(term),
                func.lower(cast(ResearchItem.authors, String)).like(term),
                ResearchItem.tags.any(func.lower(Tag.name).like(term)),
            ),
        )
    )


@router.get("", response_model=ResearchList)
def search(
    q: str = Query(min_length=1),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type_filter: str | None = Query(None, alias="type"),
    collection_method: str | None = None,
    tag: str | None = None,
) -> ResearchList:
    if settings.search_data_provider == "meilisearch":
        ids, total = MeilisearchProjectionClient.from_settings().search(
            query=q,
            page=page,
            page_size=page_size,
            type_filter=type_filter,
            collection_method=collection_method,
            tag=tag,
        )
        return ResearchList(
            items=hydrate_ranked_research(db, ids),
            total=total,
            page=page,
            page_size=page_size,
        )
    statement = search_statement(q)
    extra = []
    if type_filter:
        extra.append(ResearchItem.type == type_filter)
    if collection_method:
        extra.append(ResearchItem.collection_method == collection_method)
    if tag:
        extra.append(ResearchItem.tags.any(Tag.name == tag.lower()))
    statement = statement.where(and_(*extra)) if extra else statement
    all_items = list(db.scalars(statement.order_by(ResearchItem.updated_at.desc())).unique())
    start = (page - 1) * page_size
    return ResearchList(
        items=[serialize_research(item) for item in all_items[start : start + page_size]],
        total=len(all_items),
        page=page,
        page_size=page_size,
    )


@router.post("/semantic", response_model=ResearchList)
def semantic_search(payload: SemanticSearchRequest, db: Session = Depends(get_db)) -> ResearchList:
    query = payload.query.strip()
    if settings.vector_data_provider == "pgvector":
        ids = PgvectorProjection(embedding_client_from_settings()).search(db, query, 20)
        return ResearchList(
            items=hydrate_ranked_research(db, ids),
            total=len(ids),
            page=1,
            page_size=20,
        )
    # Local default preserves the lightweight lexical behavior until pgvector is selected.
    items = list(db.scalars(search_statement(query)).unique())
    return ResearchList(
        items=[serialize_research(item) for item in items[:20]],
        total=len(items),
        page=1,
        page_size=20,
    )


def _lexical_search(
    db: Session,
    *,
    query: str,
    limit: int,
    type_filter: str | None,
    collection_method: str | None,
    tag: str | None,
) -> list[str]:
    """Return up to ``limit`` approved research ids ranked lexically.

    Uses the configured Meilisearch projection when selected, otherwise the
    Postgres LIKE fallback used by ``GET /search`` so hybrid search keeps a
    lexical signal even when pgvector is the only selected projection.
    """
    if settings.search_data_provider == "meilisearch":
        ids, _total = MeilisearchProjectionClient.from_settings().search(
            query=query,
            page=1,
            page_size=limit,
            type_filter=type_filter,
            collection_method=collection_method,
            tag=tag,
        )
        return list(dict.fromkeys(ids))[:limit]
    statement = search_statement(query)
    extra = []
    if type_filter:
        extra.append(ResearchItem.type == type_filter)
    if collection_method:
        extra.append(ResearchItem.collection_method == collection_method)
    if tag:
        extra.append(ResearchItem.tags.any(Tag.name == tag.lower()))
    statement = statement.where(and_(*extra)) if extra else statement
    items = list(db.scalars(statement.order_by(ResearchItem.updated_at.desc())).unique())
    return [item.id for item in items[:limit]]


def _semantic_search_ids(db: Session, *, query: str, limit: int) -> list[str]:
    """Return up to ``limit`` research ids ranked by embedding similarity.

    Falls back to the lexical Postgres path when pgvector is not selected so the
    hybrid endpoint still has two lists to fuse; on a pgvector-disabled runtime
    fusion degenerates to lexical order, which is safe and shape-preserving.
    """
    if settings.vector_data_provider == "pgvector":
        return PgvectorProjection(embedding_client_from_settings()).search(db, query, limit)
    return _lexical_search(
        db, query=query, limit=limit, type_filter=None, collection_method=None, tag=None
    )


@router.post("/hybrid", response_model=ResearchList)
def hybrid_search(payload: HybridSearchRequest, db: Session = Depends(get_db)) -> ResearchList:
    if not settings.search_hybrid_enabled:
        raise HTTPException(
            status_code=404,
            detail={"code": "FEATURE_DISABLED", "message": "Hybrid search is disabled."},
        )
    query = payload.query
    limit = payload.limit
    lexical = _lexical_search(
        db,
        query=query,
        limit=limit,
        type_filter=payload.type,
        collection_method=payload.collection_method,
        tag=payload.tag,
    )
    semantic = _semantic_search_ids(db, query=query, limit=limit)
    fused = reciprocal_rank_fusion([lexical, semantic])[:limit]
    return ResearchList(
        items=hydrate_ranked_research(db, fused),
        total=len(fused),
        page=1,
        page_size=limit,
    )


@router.get("/suggest", response_model=list[str])
def suggest(q: str, db: Session = Depends(get_db)) -> list[str]:
    if settings.search_data_provider == "meilisearch":
        return MeilisearchProjectionClient.from_settings().suggest(q)
    term = f"%{q.lower()}%"
    titles = db.scalars(
        select(ResearchItem.title)
        .where(ResearchItem.status == "approved", func.lower(ResearchItem.title).like(term))
        .limit(5)
    )
    tags = db.scalars(select(Tag.display_name).where(func.lower(Tag.name).like(term)).limit(5))
    return list(dict.fromkeys([*titles, *tags]))[:8]


@router.post("/rebuild", response_model=SearchRebuildResponse)
def rebuild(payload: SearchRebuildRequest, db: Session = Depends(get_db)) -> dict:
    started = time.monotonic()
    result = rebuild_search_projections(db, payload.projections)
    logger.info(
        "Search projections rebuilt",
        extra={
            "action": "search.projections.rebuilt",
            "outcome": "success",
            "duration_ms": round((time.monotonic() - started) * 1000, 2),
            "search_document_count": result.get("meilisearch", {}).get("projected", 0),
            "vector_chunk_count": result.get("pgvector", {}).get("chunks", 0),
        },
    )
    mark_projection_rebuilt(db, target="search")
    return {"projections": result}


related_router = APIRouter(prefix="/research", tags=["search"])


@related_router.get("/{research_id}/related", response_model=list[ResearchRead])
def related(research_id: str, db: Session = Depends(get_db)) -> list[ResearchRead]:
    item = get_research_or_404(db, research_id)
    tag_ids = [tag.id for tag in item.tags]
    candidates = []
    if tag_ids:
        candidates.extend(
            db.scalars(
                select(ResearchItem)
                .join(ResearchItem.tags)
                .options(selectinload(ResearchItem.tags))
                .where(
                    ResearchItem.id != item.id,
                    ResearchItem.status == "approved",
                    Tag.id.in_(tag_ids),
                )
                .limit(10)
            ).unique()
        )
    linked_ids = list(
        db.scalars(select(ResearchRelation.target_id).where(ResearchRelation.source_id == item.id))
    )
    if linked_ids:
        candidates.extend(
            db.scalars(
                select(ResearchItem)
                .options(selectinload(ResearchItem.tags))
                .where(ResearchItem.id.in_(linked_ids), ResearchItem.status == "approved")
            )
        )
    unique = {candidate.id: candidate for candidate in candidates}
    return [serialize_research(candidate) for candidate in list(unique.values())[:10]]
