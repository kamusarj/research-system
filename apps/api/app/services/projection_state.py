"""Track whether the derived projections still match the canonical graph.

Neo4j, Meilisearch and pgvector are rebuilt copies of PostgreSQL, not live views of it.
Applying a change set moves the canonical graph and leaves those copies behind, and
nothing previously said so — a search would keep returning the pre-change answer with no
indication it was stale.

Rebuilds stay an explicit owner action. Triggering one inside ``apply`` would make a
governed, local operation depend on three external services being reachable. What is
recorded here is the *fact* that a rebuild is owed, so the UI and operators can see it.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditEvent

CANONICAL_CHANGED = "graph.canonical.changed"
PROJECTION_REBUILT = "graph.projection.rebuilt"

# Each projection is rebuilt independently, so staleness is tracked per target.
PROJECTION_TARGETS = ("graph", "search")


@dataclass(slots=True)
class ProjectionStatus:
    target: str
    stale: bool
    canonical_changed_at: datetime | None
    rebuilt_at: datetime | None

    def as_dict(self) -> dict:
        return {
            "target": self.target,
            "stale": self.stale,
            "canonical_changed_at": (
                self.canonical_changed_at.isoformat() if self.canonical_changed_at else None
            ),
            "rebuilt_at": self.rebuilt_at.isoformat() if self.rebuilt_at else None,
        }


def mark_canonical_graph_changed(db: Session, *, reason: str, entity_id: str) -> None:
    """Record that the canonical graph moved. Does not commit; the caller owns the unit."""

    db.add(
        AuditEvent(
            entity_type="graph_projection",
            entity_id=entity_id,
            action=CANONICAL_CHANGED,
            payload={"reason": reason},
        )
    )


def mark_projection_rebuilt(db: Session, *, target: str, entity_id: str = "all") -> None:
    db.add(
        AuditEvent(
            entity_type="graph_projection",
            entity_id=entity_id,
            action=PROJECTION_REBUILT,
            payload={"target": target},
        )
    )
    db.commit()


def _latest(db: Session, action: str, target: str | None = None) -> datetime | None:
    statement = select(func.max(AuditEvent.created_at)).where(AuditEvent.action == action)
    if target is not None:
        # SQLite and PostgreSQL disagree on JSON operators, so the small number of rebuild
        # rows is filtered in Python rather than in a dialect-specific predicate.
        rows = db.scalars(
            select(AuditEvent)
            .where(AuditEvent.action == action)
            .order_by(AuditEvent.created_at.desc())
            .limit(200)
        )
        for row in rows:
            if (row.payload or {}).get("target") == target:
                return row.created_at
        return None
    return db.scalar(statement)


def projection_status(db: Session) -> list[dict]:
    changed_at = _latest(db, CANONICAL_CHANGED)
    statuses: list[ProjectionStatus] = []
    for target in PROJECTION_TARGETS:
        rebuilt_at = _latest(db, PROJECTION_REBUILT, target)
        stale = changed_at is not None and (rebuilt_at is None or rebuilt_at < changed_at)
        statuses.append(ProjectionStatus(target, stale, changed_at, rebuilt_at))
    return [status.as_dict() for status in statuses]
