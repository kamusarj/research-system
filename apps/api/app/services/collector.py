import hashlib
from datetime import UTC, datetime

import feedparser
from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import CollectorRun, CollectorSource, DiscoveredItem, Evaluation, ResearchItem
from app.schemas.research import ResearchCreate
from app.services.research import create_research, transition


def score_entry(title: str, content: str) -> tuple[float, dict[str, float]]:
    text = f"{title} {content}".lower()
    keywords = ("agent", "ai", "llm", "rag", "automation", "business", "tool")
    relevance = min(100.0, 40.0 + sum(10 for keyword in keywords if keyword in text))
    quality = min(100.0, 50.0 + min(len(content) / 40, 30))
    novelty, actionability, freshness = 65.0, 70.0, 80.0
    overall = (
        relevance * 0.35 + quality * 0.2 + novelty * 0.2 + actionability * 0.15 + freshness * 0.1
    )
    breakdown = {
        "relevance": relevance,
        "quality": quality,
        "novelty": novelty,
        "actionability": actionability,
        "freshness": freshness,
    }
    return round(overall, 2), breakdown


def ingest(db: Session, discovered: DiscoveredItem) -> ResearchItem:
    item = create_research(
        db,
        ResearchCreate(
            title=discovered.title,
            type="reference",
            collection_method="auto-collected",
            content=discovered.normalized_markdown,
            source_url=discovered.source_url,
            external_id=discovered.external_id,
            authors=discovered.authors,
            metadata={
                "collector_source_id": discovered.source_id,
                "collector_run_id": discovered.run_id,
            },
        ),
    )
    transition(db, item, "submit-review")
    transition(db, item, "approve")
    discovered.research_id = item.id
    discovered.status = "ingested"
    db.commit()
    return item


def run_rss(db: Session, source: CollectorSource) -> CollectorRun:
    if not source.enabled:
        raise HTTPException(409, "Collector source is disabled")
    run = CollectorRun(source_id=source.id)
    db.add(run)
    db.commit()
    db.refresh(run)
    try:
        feed = feedparser.parse(source.url)
        if getattr(feed, "bozo", False) and not getattr(feed, "entries", []):
            raise ValueError(str(getattr(feed, "bozo_exception", "Invalid RSS feed")))
        for entry in feed.entries:
            url = str(entry.get("link", "")).strip()
            external_id = str(
                entry.get("id") or url or hashlib.sha256(str(entry).encode()).hexdigest()
            )
            duplicate = db.scalar(
                select(DiscoveredItem).where(
                    DiscoveredItem.source_id == source.id,
                    or_(
                        DiscoveredItem.external_id == external_id, DiscoveredItem.source_url == url
                    ),
                )
            )
            if duplicate:
                continue
            content = str(entry.get("summary") or entry.get("description") or "")
            score, breakdown = score_entry(str(entry.get("title", "Untitled")), content)
            if score >= source.auto_approve_threshold:
                decision = "auto-approved"
            elif score < source.auto_reject_threshold:
                decision = "rejected"
            else:
                decision = "needs-review"
            discovered = DiscoveredItem(
                source_id=source.id,
                run_id=run.id,
                external_id=external_id,
                source_url=url,
                title=str(entry.get("title", "Untitled")),
                normalized_markdown=content,
                authors=[
                    author.get("name") for author in entry.get("authors", []) if author.get("name")
                ],
                status=decision,
                score=score,
                score_breakdown=breakdown,
            )
            db.add(discovered)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                continue
            run.discovered_count += 1
            db.add(
                Evaluation(
                    discovered_item_id=discovered.id,
                    overall_score=score,
                    score_breakdown=breakdown,
                    decision=decision,
                    reasoning="Deterministic weighted MVP score",
                )
            )
            if decision == "auto-approved":
                ingest(db, discovered)
                run.ingested_count += 1
        run.status = "completed"
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
    run.finished_at = datetime.now(UTC)
    db.commit()
    db.refresh(run)
    return run
