"""Turn an approved link submission into a reviewable ontology change set.

Uploaded documents already reach the canonical hierarchy through
``ontology_mapping.create_document_change_set``. Link submissions did not: approving one
created a ``ResearchItem`` that appeared in the flat relationship projection and nowhere
in the hierarchy, so eleven of the twelve system boards stayed empty no matter how many
URLs were collected.

This module closes that gap using the same governance the document path uses. Nothing is
written to the canonical graph here — every proposal lands in a draft change set that a
human validates, edits and applies.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    GraphChangeSet,
    GraphMutation,
    KnowledgeNode,
    LinkSubmission,
    NodeEvidence,
)
from app.services.ontology import ROOT_KEY, normalize_ontology_key, ontology_id
from app.services.ontology_mapping import ontology_candidates
from app.services.placement import rank_pillar_placements

# Which classification fields become canonical nodes, and the ontology type each one takes.
# Tags are deliberately excluded: they are a workspace convenience, not an ontology claim.
TAXONOMY_FIELDS: tuple[tuple[str, str], ...] = (
    ("concepts", "Concept"),
    ("technologies", "Technology"),
    ("agent_patterns", "AgentPattern"),
    ("business_domains", "BusinessDomain"),
)

# A change set a reviewer cannot finish is a change set nobody opens.
MAX_PROPOSED_NODES = 40
MAX_EVIDENCE_PER_NODE = 3
MAX_EVIDENCE_EXCERPT_CHARS = 600


def _pillar_nodes(db: Session) -> dict[str, str]:
    """Map each approved pillar's canonical label to its node ID."""

    rows = db.scalars(
        select(KnowledgeNode).where(
            KnowledgeNode.node_type == "SystemPillar",
            KnowledgeNode.lifecycle_status == "approved",
        )
    )
    return {node.canonical_label: node.id for node in rows}


def resolve_parent_id(db: Session, title: str, content: str) -> str:
    """Choose the pillar a submission belongs under, falling back to the root.

    Placing an unroutable source at the root is honest — it says "this belongs in the
    system but we do not know where" — and keeps it visible for a reviewer to move.
    """

    pillars = _pillar_nodes(db)
    for label, _score in rank_pillar_placements(f"{title}\n{content[:4000]}", limit=3):
        if label in pillars:
            return pillars[label]
    return ontology_id(ROOT_KEY)


def _classified_labels(classification: dict) -> list[tuple[str, str]]:
    """Collect (label, node_type) pairs, keeping the first casing seen for each label."""

    seen: dict[str, tuple[str, str]] = {}
    for field, node_type in TAXONOMY_FIELDS:
        for value in classification.get(field) or []:
            if not isinstance(value, str):
                continue
            label = value.strip()
            key = normalize_ontology_key(label)
            if not label or not key or key in seen:
                continue
            seen[key] = (label, node_type)
    return list(seen.values())


def _record_evidence(
    db: Session,
    item: LinkSubmission,
    label: str,
    excerpts: list[dict],
    research_id: str | None,
) -> list[str]:
    """Persist the source excerpts that justify one proposed node.

    Excerpts mentioning the label are preferred so a reviewer sees why the node was
    proposed rather than a generic opening paragraph.
    """

    needle = label.casefold()
    ranked = sorted(
        excerpts,
        key=lambda excerpt: needle not in str(excerpt.get("text", "")).casefold(),
    )
    evidence_ids: list[str] = []
    for excerpt in ranked[:MAX_EVIDENCE_PER_NODE]:
        text = str(excerpt.get("text") or "").strip()
        if not text:
            continue
        evidence = NodeEvidence(
            owner_kind="link_submission",
            owner_id=item.id,
            source_document_id=research_id,
            excerpt=text[:MAX_EVIDENCE_EXCERPT_CHARS],
            location={
                "url": item.url,
                "location": excerpt.get("location"),
                "section": excerpt.get("section"),
            },
            extraction_method="link-intake-v1",
            provenance={
                "link_submission_id": item.id,
                "provider": item.provider_name,
                "model": item.model_name,
                "proposed_for": label,
            },
        )
        db.add(evidence)
        db.flush()
        evidence_ids.append(evidence.id)
    return evidence_ids


def create_link_change_set(
    db: Session, item: LinkSubmission, research_id: str | None = None
) -> GraphChangeSet | None:
    """Propose canonical placements for one approved submission.

    Returns ``None`` when the submission carries nothing to place — an unclassified
    source, or one whose concepts are all already in the graph with evidence. That is a
    normal outcome, not a failure, so approval is never blocked by it.
    """

    existing = db.scalar(
        select(GraphChangeSet).where(
            GraphChangeSet.origin_type == "link_submission",
            GraphChangeSet.origin_id == item.id,
            GraphChangeSet.lifecycle_status.notin_({"rejected", "superseded"}),
        )
    )
    if existing is not None:
        return existing

    classification = item.classification or {}
    labels = _classified_labels(classification)
    if not labels:
        return None

    normalized_source = classification.get("normalized_source") or {}
    excerpts = [
        excerpt
        for excerpt in (normalized_source.get("evidence") or [])
        if isinstance(excerpt, dict)
    ]
    if not excerpts:
        # Without a verbatim excerpt every mutation would fail EVIDENCE_REQUIRED, so the
        # source summary stands in as the one thing that is quotable.
        summary = str(classification.get("summary") or normalized_source.get("description") or "")
        if not summary.strip():
            return None
        excerpts = [{"text": summary, "location": "summary"}]

    title = item.title or item.url
    parent_id = resolve_parent_id(db, title, item.extracted_markdown or "")
    change_set = GraphChangeSet(
        origin_type="link_submission",
        origin_id=item.id,
        title=f"Sắp xếp tri thức từ {title}"[:300],
        summary=(
            f"Review {min(len(labels), MAX_PROPOSED_NODES)} canonical placements extracted "
            f"from {item.url}."
        ),
        lifecycle_status="draft",
        validation_summary={},
        created_by="link-mapping-v1",
    )
    db.add(change_set)
    db.flush()

    order = 0
    for label, node_type in labels[:MAX_PROPOSED_NODES]:
        candidates = ontology_candidates(db, label, node_type=node_type)
        exact = next((candidate for candidate in candidates if candidate.score == 1), None)
        evidence_ids = _record_evidence(db, item, label, excerpts, research_id)
        if not evidence_ids:
            continue
        if exact is not None:
            operation = "ATTACH_EVIDENCE"
            target_id = exact.node_id
            proposed = {
                "action": "MATCH_EXISTING",
                "source_label": label,
                "target_node_id": target_id,
                "target_label": exact.canonical_label,
                "evidence_ids": evidence_ids,
                "candidates": [candidate.model_dump() for candidate in candidates],
            }
        else:
            operation = "CREATE_NODE"
            target_id = str(uuid.uuid4())
            proposed = {
                "action": "CREATE_NEW" if not candidates else "RELATED_BUT_DISTINCT",
                "canonical_label": label,
                "node_type": node_type,
                "normalized_key": normalize_ontology_key(label),
                "description": "",
                "primary_parent_id": parent_id,
                "confidence": float(classification.get("confidence") or 0),
                "evidence_ids": evidence_ids,
                "candidates": [candidate.model_dump() for candidate in candidates],
            }
        db.add(
            GraphMutation(
                change_set_id=change_set.id,
                mutation_order=order,
                operation=operation,
                target_kind="node",
                target_id=target_id,
                proposed_json=proposed,
                validation_status="pending",
                validation_messages=[],
                review_decision="pending",
            )
        )
        order += 1

    if order == 0:
        db.delete(change_set)
        db.flush()
        return None
    db.flush()
    return change_set

