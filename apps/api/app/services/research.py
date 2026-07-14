import re
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    AuditEvent,
    Comment,
    OutboxEvent,
    ResearchItem,
    ResearchRelation,
    ResearchVersion,
    Tag,
)
from app.schemas.research import ResearchCreate, ResearchRead, ResearchUpdate


def normalize_tag(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not normalized:
        raise HTTPException(422, "Tag must contain letters or numbers")
    return normalized


def serialize_research(item: ResearchItem) -> ResearchRead:
    return ResearchRead(
        id=item.id,
        display_id=item.display_id or item.id,
        title=item.title,
        type=item.type,
        status=item.status,
        collection_method=item.collection_method,
        summary=item.summary,
        content=item.content,
        source_url=item.source_url,
        authors=item.authors or [],
        tags=[tag.display_name for tag in item.tags],
        metadata=item.metadata_json or {},
        created_at=item.created_at,
        updated_at=item.updated_at,
        approved_at=item.approved_at,
    )


def get_research_or_404(db: Session, research_id: str) -> ResearchItem:
    item = db.scalar(
        select(ResearchItem)
        .options(selectinload(ResearchItem.tags))
        .where((ResearchItem.id == research_id) | (ResearchItem.display_id == research_id))
    )
    if not item:
        raise HTTPException(404, "Research item not found")
    return item


def sync_tags(db: Session, item: ResearchItem, values: list[str]) -> None:
    tags: list[Tag] = []
    for value in values:
        name = normalize_tag(value)
        tag = db.scalar(select(Tag).where(Tag.name == name))
        if not tag:
            tag = Tag(name=name, display_name=value.strip())
            db.add(tag)
            db.flush()
        tags.append(tag)
    item.tags = tags


def snapshot(item: ResearchItem) -> dict[str, object]:
    return {
        "title": item.title,
        "type": item.type,
        "status": item.status,
        "collection_method": item.collection_method,
        "summary": item.summary,
        "content": item.content,
        "source_url": item.source_url,
        "authors": item.authors,
        "tags": [tag.display_name for tag in item.tags],
        "metadata": item.metadata_json,
    }


def record_event(db: Session, item: ResearchItem, event_type: str) -> None:
    db.add_all(
        [
            AuditEvent(entity_type="research", entity_id=item.id, action=event_type),
            OutboxEvent(event_type=event_type, aggregate_id=item.id, payload={"id": item.id}),
        ]
    )


def create_research(db: Session, data: ResearchCreate) -> ResearchItem:
    values = data.model_dump(exclude={"tags", "metadata"}, mode="json")
    values["source_url"] = str(data.source_url) if data.source_url else None
    item = ResearchItem(**values, metadata_json=data.metadata)
    db.add(item)
    db.flush()
    item.display_id = f"RES-{datetime.now(UTC).year}-{item.id[:8].upper()}"
    sync_tags(db, item, data.tags)
    record_event(db, item, "research.created")
    db.commit()
    db.refresh(item)
    return get_research_or_404(db, item.id)


def update_research(db: Session, item: ResearchItem, data: ResearchUpdate) -> ResearchItem:
    version_number = db.scalar(
        select(func.count())
        .select_from(ResearchVersion)
        .where(ResearchVersion.research_id == item.id)
    )
    db.add(
        ResearchVersion(
            research_id=item.id,
            version_number=(version_number or 0) + 1,
            snapshot=snapshot(item),
        )
    )
    changes = data.model_dump(exclude_unset=True, exclude={"tags", "metadata"}, mode="json")
    if "source_url" in changes and changes["source_url"] is not None:
        changes["source_url"] = str(changes["source_url"])
    for field, value in changes.items():
        setattr(item, field, value)
    if data.tags is not None:
        sync_tags(db, item, data.tags)
    if data.metadata is not None:
        item.metadata_json = data.metadata
    record_event(db, item, "research.updated")
    db.commit()
    return get_research_or_404(db, item.id)


def transition(db: Session, item: ResearchItem, action: str) -> ResearchItem:
    transitions = {
        "submit-review": ({"draft", "rejected"}, "in-review"),
        "approve": ({"in-review"}, "approved"),
        "reject": ({"in-review"}, "rejected"),
        "archive": ({"draft", "in-review", "approved", "rejected"}, "archived"),
    }
    allowed, target = transitions[action]
    if item.status not in allowed:
        raise HTTPException(409, f"Cannot {action} research in status {item.status}")
    item.status = target
    if target == "approved":
        item.approved_at = datetime.now(UTC)
    record_event(db, item, f"research.{target}")
    db.commit()
    return get_research_or_404(db, item.id)


def add_comment(db: Session, item: ResearchItem, body: str, author: str) -> Comment:
    comment = Comment(research_id=item.id, body=body, author=author)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def add_relation(
    db: Session,
    item: ResearchItem,
    target_id: str,
    relation_type: str,
    confidence: float | None,
    reasoning: str | None,
) -> ResearchRelation:
    target = get_research_or_404(db, target_id)
    if target.id == item.id:
        raise HTTPException(422, "A research item cannot relate to itself")
    existing = db.scalar(
        select(ResearchRelation).where(
            ResearchRelation.source_id == item.id,
            ResearchRelation.target_id == target.id,
            ResearchRelation.relation_type == relation_type,
        )
    )
    if existing:
        raise HTTPException(409, "Relation already exists")
    relation = ResearchRelation(
        source_id=item.id,
        target_id=target.id,
        relation_type=relation_type,
        discovered_by="manual",
        confidence=confidence,
        reasoning=reasoning,
    )
    db.add(relation)
    record_event(db, item, "research.relation-created")
    db.commit()
    db.refresh(relation)
    return relation
