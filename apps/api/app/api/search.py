from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import ResearchItem, ResearchRelation, Tag
from app.schemas.research import ResearchList, ResearchRead
from app.services.research import get_research_or_404, serialize_research

router = APIRouter(prefix="/search", tags=["search"])


def search_statement(q: str):
    term = f"%{q.lower().strip()}%"
    return (
        select(ResearchItem)
        .outerjoin(ResearchItem.tags)
        .options(selectinload(ResearchItem.tags))
        .where(
            ResearchItem.status == "approved",
            or_(
                func.lower(ResearchItem.title).like(term),
                func.lower(func.coalesce(ResearchItem.summary, "")).like(term),
                func.lower(ResearchItem.content).like(term),
                func.lower(cast(ResearchItem.authors, String)).like(term),
                func.lower(func.coalesce(Tag.name, "")).like(term),
            ),
        )
        .distinct()
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
    statement = search_statement(q)
    extra = []
    if type_filter:
        extra.append(ResearchItem.type == type_filter)
    if collection_method:
        extra.append(ResearchItem.collection_method == collection_method)
    if tag:
        extra.append(Tag.name == tag.lower())
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
def semantic_search(payload: dict[str, str], db: Session = Depends(get_db)) -> ResearchList:
    # The lightweight MVP preserves the semantic API contract and uses lexical fallback.
    query = payload.get("query", "").strip()
    if not query:
        return ResearchList(items=[], total=0, page=1, page_size=20)
    items = list(db.scalars(search_statement(query)).unique())
    return ResearchList(
        items=[serialize_research(item) for item in items[:20]],
        total=len(items),
        page=1,
        page_size=20,
    )


@router.get("/suggest", response_model=list[str])
def suggest(q: str, db: Session = Depends(get_db)) -> list[str]:
    term = f"%{q.lower()}%"
    titles = db.scalars(
        select(ResearchItem.title)
        .where(ResearchItem.status == "approved", func.lower(ResearchItem.title).like(term))
        .limit(5)
    )
    tags = db.scalars(select(Tag.display_name).where(func.lower(Tag.name).like(term)).limit(5))
    return list(dict.fromkeys([*titles, *tags]))[:8]


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
