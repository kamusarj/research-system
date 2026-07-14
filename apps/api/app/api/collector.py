from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CollectorRun, CollectorSource, DiscoveredItem
from app.schemas.collector import ReviewUpdate, SourceCreate, SourceRead, SourceUpdate
from app.services.collector import ingest, run_rss

router = APIRouter(prefix="/collector", tags=["collector"])


def source_dict(source: CollectorSource) -> SourceRead:
    return SourceRead(
        id=source.id,
        key=source.key,
        name=source.name,
        type=source.type,
        url=source.url,
        enabled=source.enabled,
        auto_approve_threshold=source.auto_approve_threshold,
        auto_reject_threshold=source.auto_reject_threshold,
        config=source.config,
        created_at=source.created_at,
    )


def get_source(db: Session, source_id: str) -> CollectorSource:
    source = db.scalar(select(CollectorSource).where(CollectorSource.id == source_id))
    if not source:
        raise HTTPException(404, "Collector source not found")
    return source


def discovered_dict(item: DiscoveredItem) -> dict:
    return {
        "id": item.id,
        "source_id": item.source_id,
        "run_id": item.run_id,
        "title": item.title,
        "source_url": item.source_url,
        "content": item.normalized_markdown,
        "authors": item.authors,
        "status": item.status,
        "score": item.score,
        "score_breakdown": item.score_breakdown,
        "research_id": item.research_id,
        "created_at": item.created_at,
    }


@router.get("/sources", response_model=list[SourceRead])
def sources(db: Session = Depends(get_db)) -> list[SourceRead]:
    return [source_dict(source) for source in db.scalars(select(CollectorSource))]


@router.post("/sources", response_model=SourceRead, status_code=201)
def create_source(data: SourceCreate, db: Session = Depends(get_db)) -> SourceRead:
    if data.auto_reject_threshold > data.auto_approve_threshold:
        raise HTTPException(422, "Reject threshold must not exceed approve threshold")
    source = CollectorSource(**data.model_dump(mode="json"))
    source.url = str(data.url)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source_dict(source)


@router.put("/sources/{source_id}", response_model=SourceRead)
def update_source(source_id: str, data: SourceUpdate, db: Session = Depends(get_db)) -> SourceRead:
    source = get_source(db, source_id)
    for field, value in data.model_dump(exclude_unset=True, mode="json").items():
        setattr(source, field, str(value) if field == "url" and value else value)
    if source.auto_reject_threshold > source.auto_approve_threshold:
        raise HTTPException(422, "Reject threshold must not exceed approve threshold")
    db.commit()
    db.refresh(source)
    return source_dict(source)


@router.post("/sources/{source_id}/run")
def run(source_id: str, db: Session = Depends(get_db)) -> dict:
    result = run_rss(db, get_source(db, source_id))
    return {
        "id": result.id,
        "status": result.status,
        "discovered_count": result.discovered_count,
        "ingested_count": result.ingested_count,
        "error": result.error,
    }


@router.get("/runs")
def runs(db: Session = Depends(get_db)) -> list[dict]:
    return [
        {
            "id": run.id,
            "source_id": run.source_id,
            "status": run.status,
            "discovered_count": run.discovered_count,
            "ingested_count": run.ingested_count,
            "error": run.error,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
        }
        for run in db.scalars(select(CollectorRun).order_by(CollectorRun.started_at.desc()))
    ]


@router.get("/review-queue")
def review_queue(db: Session = Depends(get_db)) -> list[dict]:
    return [
        discovered_dict(item)
        for item in db.scalars(
            select(DiscoveredItem)
            .where(DiscoveredItem.status == "needs-review")
            .order_by(DiscoveredItem.score.desc())
        )
    ]


def get_discovered(db: Session, item_id: str) -> DiscoveredItem:
    item = db.scalar(select(DiscoveredItem).where(DiscoveredItem.id == item_id))
    if not item:
        raise HTTPException(404, "Discovered item not found")
    if item.status != "needs-review":
        raise HTTPException(409, f"Item cannot be reviewed in status {item.status}")
    return item


@router.post("/review-queue/{item_id}/approve")
def approve(item_id: str, db: Session = Depends(get_db)) -> dict:
    item = get_discovered(db, item_id)
    research = ingest(db, item)
    return {"status": item.status, "research_id": research.id}


@router.post("/review-queue/{item_id}/reject")
def reject(item_id: str, db: Session = Depends(get_db)) -> dict:
    item = get_discovered(db, item_id)
    item.status = "rejected"
    db.commit()
    return discovered_dict(item)


@router.post("/review-queue/{item_id}/edit-and-approve")
def edit_and_approve(item_id: str, data: ReviewUpdate, db: Session = Depends(get_db)) -> dict:
    item = get_discovered(db, item_id)
    if data.title is not None:
        item.title = data.title
    if data.content is not None:
        item.normalized_markdown = data.content
    research = ingest(db, item)
    return {"status": item.status, "research_id": research.id}
