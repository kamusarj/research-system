from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Attachment, Comment, ResearchItem, ResearchRelation, ResearchVersion, Tag
from app.schemas.research import (
    AttachmentCreate,
    AttachmentRead,
    CommentCreate,
    CommentRead,
    RelationCreate,
    RelationRead,
    ResearchCreate,
    ResearchList,
    ResearchRead,
    ResearchUpdate,
    VersionRead,
)
from app.services.research import (
    add_comment,
    add_relation,
    create_research,
    get_research_or_404,
    serialize_research,
    transition,
    update_research,
)

router = APIRouter(prefix="/research", tags=["research"])


@router.get("", response_model=ResearchList)
def list_research(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    type_filter: str | None = Query(None, alias="type"),
    collection_method: str | None = None,
    tag: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> ResearchList:
    query = select(ResearchItem).options(selectinload(ResearchItem.tags))
    count_query = select(func.count()).select_from(ResearchItem)
    filters = []
    if status_filter:
        filters.append(ResearchItem.status == status_filter)
    else:
        filters.append(ResearchItem.status != "archived")
    if type_filter:
        filters.append(ResearchItem.type == type_filter)
    if collection_method:
        filters.append(ResearchItem.collection_method == collection_method)
    if created_from:
        filters.append(ResearchItem.created_at >= created_from)
    if created_to:
        filters.append(ResearchItem.created_at <= created_to)
    if tag:
        query = query.join(ResearchItem.tags).where(Tag.name == tag.lower())
        count_query = count_query.join(ResearchItem.tags).where(Tag.name == tag.lower())
    query = query.where(*filters)
    count_query = count_query.where(*filters)
    items = db.scalars(
        query.order_by(ResearchItem.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return ResearchList(
        items=[serialize_research(item) for item in items],
        total=db.scalar(count_query) or 0,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ResearchRead, status_code=status.HTTP_201_CREATED)
def create(data: ResearchCreate, db: Session = Depends(get_db)) -> ResearchRead:
    return serialize_research(create_research(db, data))


@router.get("/{research_id}", response_model=ResearchRead)
def get(research_id: str, db: Session = Depends(get_db)) -> ResearchRead:
    return serialize_research(get_research_or_404(db, research_id))


@router.put("/{research_id}", response_model=ResearchRead)
def update(research_id: str, data: ResearchUpdate, db: Session = Depends(get_db)) -> ResearchRead:
    return serialize_research(update_research(db, get_research_or_404(db, research_id), data))


@router.delete("/{research_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(research_id: str, db: Session = Depends(get_db)) -> Response:
    transition(db, get_research_or_404(db, research_id), "archive")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{research_id}/submit-review", response_model=ResearchRead)
def submit_review(research_id: str, db: Session = Depends(get_db)) -> ResearchRead:
    return serialize_research(transition(db, get_research_or_404(db, research_id), "submit-review"))


@router.post("/{research_id}/approve", response_model=ResearchRead)
def approve(research_id: str, db: Session = Depends(get_db)) -> ResearchRead:
    return serialize_research(transition(db, get_research_or_404(db, research_id), "approve"))


@router.post("/{research_id}/reject", response_model=ResearchRead)
def reject(research_id: str, db: Session = Depends(get_db)) -> ResearchRead:
    return serialize_research(transition(db, get_research_or_404(db, research_id), "reject"))


@router.post("/{research_id}/archive", response_model=ResearchRead)
def archive(research_id: str, db: Session = Depends(get_db)) -> ResearchRead:
    return serialize_research(transition(db, get_research_or_404(db, research_id), "archive"))


@router.get("/{research_id}/versions", response_model=list[VersionRead])
def versions(research_id: str, db: Session = Depends(get_db)) -> list[ResearchVersion]:
    item = get_research_or_404(db, research_id)
    return list(
        db.scalars(
            select(ResearchVersion)
            .where(ResearchVersion.research_id == item.id)
            .order_by(ResearchVersion.version_number.desc())
        )
    )


@router.get("/{research_id}/comments", response_model=list[CommentRead])
def comments(research_id: str, db: Session = Depends(get_db)) -> list[Comment]:
    item = get_research_or_404(db, research_id)
    return list(db.scalars(select(Comment).where(Comment.research_id == item.id)))


@router.post("/{research_id}/comments", response_model=CommentRead, status_code=201)
def comment(research_id: str, data: CommentCreate, db: Session = Depends(get_db)) -> Comment:
    return add_comment(db, get_research_or_404(db, research_id), data.body, data.author)


@router.get("/{research_id}/relations", response_model=list[RelationRead])
def relations(research_id: str, db: Session = Depends(get_db)) -> list[ResearchRelation]:
    item = get_research_or_404(db, research_id)
    return list(db.scalars(select(ResearchRelation).where(ResearchRelation.source_id == item.id)))


@router.post("/{research_id}/relations", response_model=RelationRead, status_code=201)
def relation(
    research_id: str, data: RelationCreate, db: Session = Depends(get_db)
) -> ResearchRelation:
    return add_relation(
        db,
        get_research_or_404(db, research_id),
        data.target_id,
        data.relation_type,
        data.confidence,
        data.reasoning,
    )


@router.get("/{research_id}/attachments", response_model=list[AttachmentRead])
def attachments(research_id: str, db: Session = Depends(get_db)) -> list[Attachment]:
    item = get_research_or_404(db, research_id)
    return list(db.scalars(select(Attachment).where(Attachment.research_id == item.id)))


@router.post("/{research_id}/attachments", response_model=AttachmentRead, status_code=201)
def add_attachment(
    research_id: str, data: AttachmentCreate, db: Session = Depends(get_db)
) -> Attachment:
    item = get_research_or_404(db, research_id)
    attachment = Attachment(research_id=item.id, **data.model_dump())
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment
