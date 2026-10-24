from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditEvent, KnowledgeGap, ResearchItem, Tag, research_tags
from app.schemas.research import ResearchCreate
from app.services.research import create_research, transition


def serialize_gap(gap: KnowledgeGap) -> dict:
    return {
        "id": gap.id,
        "key": gap.key,
        "title": gap.title,
        "concept_key": gap.concept_key,
        "status": gap.status,
        "priority": gap.priority,
        "coverage_count": gap.coverage_count,
        "reason": gap.reason,
        "assigned_to": gap.assigned_to,
        "snoozed_until": gap.snoozed_until,
        "deep_research_id": gap.deep_research_id,
        "metadata": gap.metadata_json or {},
        "created_at": gap.created_at,
        "updated_at": gap.updated_at,
    }


def get_gap(db: Session, gap_id: str) -> KnowledgeGap:
    gap = db.scalar(select(KnowledgeGap).where(KnowledgeGap.id == gap_id))
    if not gap:
        raise HTTPException(404, "Knowledge gap not found")
    return gap


def _snooze_expired(gap: KnowledgeGap) -> bool:
    if gap.status != "snoozed" or gap.snoozed_until is None:
        return False
    until = gap.snoozed_until
    # SQLite trả về datetime không có múi giờ; giá trị được lưu theo UTC.
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    return until <= datetime.now(UTC)


def detect_gaps(db: Session, max_coverage: int = 1, *, commit: bool = True) -> list[KnowledgeGap]:
    rows = db.execute(
        select(Tag.name, Tag.display_name, func.count(ResearchItem.id))
        .join(research_tags, research_tags.c.tag_id == Tag.id)
        .join(ResearchItem, ResearchItem.id == research_tags.c.research_id)
        .where(ResearchItem.status == "approved")
        .group_by(Tag.id, Tag.name, Tag.display_name)
    ).all()
    detected_keys: set[str] = set()
    for concept_key, display_name, coverage in rows:
        if concept_key == "deep-research":
            continue
        key = f"low-coverage:{concept_key}"
        gap = db.scalar(select(KnowledgeGap).where(KnowledgeGap.key == key))
        reason = (
            f"Khái niệm “{display_name}” mới có {coverage} tài liệu nghiên cứu được duyệt; "
            "bổ sung bằng chứng sẽ giúp tăng độ phủ của đồ thị."
        )
        if coverage > max_coverage:
            if gap:
                gap.coverage_count = coverage
                gap.reason = (
                    f"Khái niệm “{display_name}” hiện có {coverage} tài liệu nghiên cứu được duyệt."
                )
                if gap.status not in {"dismissed", "deep-research-requested"}:
                    gap.status = "filled"
            continue
        detected_keys.add(key)
        if gap:
            gap.coverage_count = coverage
            gap.reason = reason
            if gap.status == "filled" or _snooze_expired(gap):
                gap.status = "detected"
                gap.snoozed_until = None
        else:
            gap = KnowledgeGap(
                key=key,
                title=f"Mở rộng độ phủ cho {display_name}",
                concept_key=concept_key,
                coverage_count=coverage,
                reason=reason,
                metadata_json={"detector": "graph-low-coverage-v1", "threshold": max_coverage},
            )
            db.add(gap)

    active = db.scalars(
        select(KnowledgeGap).where(
            KnowledgeGap.key.like("low-coverage:%"),
            KnowledgeGap.status.not_in({"dismissed", "deep-research-requested"}),
        )
    )
    for gap in active:
        if gap.key not in detected_keys:
            gap.status = "filled"
    if commit:
        db.commit()
    else:
        db.flush()
    return list(
        db.scalars(
            select(KnowledgeGap).order_by(
                KnowledgeGap.priority.desc(), KnowledgeGap.updated_at.desc()
            )
        )
    )


def list_gaps(db: Session) -> list[KnowledgeGap]:
    return list(
        db.scalars(
            select(KnowledgeGap).order_by(
                KnowledgeGap.priority.desc(), KnowledgeGap.updated_at.desc()
            )
        )
    )


def request_deep_research(db: Session, gap: KnowledgeGap) -> ResearchItem:
    if gap.status in {"dismissed", "filled"}:
        raise HTTPException(409, f"Cannot research a gap in status {gap.status}")
    if gap.deep_research_id:
        existing = db.get(ResearchItem, gap.deep_research_id)
        if existing:
            return existing
    item = create_research(
        db,
        ResearchCreate(
            title=f"Nghiên cứu sâu: {gap.title}",
            type="deep-research-report",
            collection_method="ai-researched",
            summary=f"Bản nháp báo cáo dành cho khoảng trống tri thức: {gap.title}.",
            content=(
                f"# {gap.title}\n\n"
                "## Câu hỏi nghiên cứu\n\n"
                f"{gap.reason}\n\n"
                "## Bằng chứng\n\nBổ sung bằng chứng có nguồn tại đây.\n\n"
                "## Phát hiện\n\nCác phát hiện nháp đang chờ con người kiểm duyệt.\n"
            ),
            tags=[gap.concept_key, "nghiên cứu sâu"],
            metadata={
                "knowledge_gap_id": gap.id,
                "requested_at": datetime.now(UTC).isoformat(),
                "human_approval_required": True,
            },
        ),
    )
    gap.deep_research_id = item.id
    gap.status = "deep-research-requested"
    db.add(
        AuditEvent(
            entity_type="knowledge-gap",
            entity_id=gap.id,
            action="gap.deep-research-requested",
            payload={"research_id": item.id},
        )
    )
    db.commit()
    return item


def approve_deep_research(db: Session, research_id: str) -> ResearchItem:
    item = db.get(ResearchItem, research_id)
    if not item or item.type != "deep-research-report":
        raise HTTPException(404, "Deep research report not found")
    if item.status != "in-review":
        raise HTTPException(409, "Deep research must be submitted for human review first")
    item = transition(db, item, "approve")
    gap = db.scalar(select(KnowledgeGap).where(KnowledgeGap.deep_research_id == item.id))
    if gap:
        gap.status = "filled"
        db.commit()
    return item
