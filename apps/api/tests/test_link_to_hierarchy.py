"""Prove that submitting a link can put knowledge into the canonical hierarchy.

This is the path the project existed to provide and did not have: before these tests,
approving a link produced a ``ResearchItem`` in the flat relationship view while every
system pillar in the hierarchy stayed empty.
"""

from sqlalchemy import select

from app.models import GraphChangeSet, GraphMutation, KnowledgeGap, KnowledgeNode, LinkSubmission
from app.schemas.ingestion import LinkReview
from app.services.graph import ontology_graph_projection
from app.services.graph_changes import apply_change_set, approve_change_set, validate_change_set
from app.services.ingestion import approve_submission
from app.services.link_mapping import create_link_change_set, resolve_parent_id
from app.services.ontology import ROOT_KEY, ensure_seed_ontology, ontology_id

CLASSIFICATION = {
    "content_type": "article",
    "language": "en",
    "summary": "How retrieval pipelines keep business agent memory current.",
    "concepts": ["Retrieval Augmented Memory"],
    "technologies": ["pgvector"],
    "agent_patterns": [],
    "business_domains": [],
    "tags": ["memory"],
    "relations": [],
    "relevance_score": 0.9,
    "confidence": 0.91,
    "reasoning": "Grounded in the source text.",
    "normalized_source": {
        "source_type": "article",
        "evidence": [
            {
                "id": "article:1:evidence:0",
                "text": "Retrieval augmented memory keeps an agent's knowledge current "
                "between runs without retraining the model.",
                "location": "paragraph:1",
            },
            {
                "id": "article:1:evidence:1",
                "text": "The reference implementation stores embeddings in pgvector and "
                "rebuilds the index on every approved change.",
                "location": "paragraph:2",
            },
        ],
    },
}


def _submission(db, **overrides) -> LinkSubmission:
    ensure_seed_ontology(db)
    fields = {
        "url": "https://publisher.example/agent-memory",
        "source_type": "manual",
        "status": "completed",
        "stage": "completed",
        "review_status": "needs_review",
        "title": "Keeping business agent memory current",
        "extracted_markdown": "A grounded report about retrieval augmented memory for agents.",
        "content_hash": "hash-agent-memory",
        "classification": CLASSIFICATION,
        "provider_name": "deepseek",
        "model_name": "deepseek-v4-pro",
        **overrides,
    }
    item = LinkSubmission(**fields)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def test_approving_a_link_proposes_placements_instead_of_silently_dropping_them(client, db):
    item = _submission(db)

    approve_submission(db, item, LinkReview())

    change_set = db.scalar(select(GraphChangeSet).where(GraphChangeSet.origin_id == item.id))
    mutations = list(
        db.scalars(select(GraphMutation).where(GraphMutation.change_set_id == change_set.id))
    )

    assert change_set.origin_type == "link_submission"
    assert change_set.lifecycle_status == "draft"
    assert {mutation.proposed_json["canonical_label"] for mutation in mutations} == {
        "Retrieval Augmented Memory",
        "pgvector",
    }
    # Nothing has reached the canonical graph yet; a human still has to say yes.
    assert (
        db.scalar(select(KnowledgeNode).where(KnowledgeNode.canonical_label == "pgvector")) is None
    )
    gap = db.scalar(select(KnowledgeGap).where(KnowledgeGap.key == "low-coverage:memory"))
    assert gap is not None
    assert gap.status == "detected"
    assert gap.coverage_count == 1


def test_applying_the_proposal_makes_the_link_visible_in_the_hierarchy(client, db):
    item = _submission(db)
    approve_submission(db, item, LinkReview())
    change_set = db.scalar(select(GraphChangeSet).where(GraphChangeSet.origin_id == item.id))

    before = {node["label"] for node in ontology_graph_projection(db)["nodes"]}
    validate_change_set(db, change_set)
    for mutation in change_set_mutations(db, change_set.id):
        mutation.review_decision = "accepted"
    db.commit()
    approve_change_set(db, change_set)
    apply_change_set(db, change_set)

    projection = ontology_graph_projection(db)
    labels = {node["label"] for node in projection["nodes"]}
    placed = next(node for node in projection["nodes"] if node["label"] == "pgvector")
    parents = {
        edge["target"]: edge["source"]
        for edge in projection["edges"]
        if edge["type"] == "PARENT_OF"
    }

    assert "pgvector" not in before
    assert {"Retrieval Augmented Memory", "pgvector"} <= labels
    # The point of the exercise: the new node hangs off the hierarchy, not in isolation.
    assert parents[placed["id"]] == placed["primary_parent_id"]


def test_every_proposal_carries_the_excerpt_that_justifies_it(client, db):
    item = _submission(db)

    change_set = create_link_change_set(db, item)
    db.commit()
    validate_change_set(db, change_set)
    mutations = change_set_mutations(db, change_set.id)

    assert mutations
    for mutation in mutations:
        # A mutation with no excerpt fails EVIDENCE_REQUIRED, which is exactly the check
        # that stops an unsupported claim from entering the canonical graph.
        assert mutation.proposed_json["evidence_ids"]
        assert not [
            message for message in mutation.validation_messages if message["level"] == "error"
        ]


def test_a_submission_with_nothing_to_place_does_not_create_an_empty_change_set(client, db):
    item = _submission(db, classification={"summary": "", "concepts": [], "technologies": []})

    assert create_link_change_set(db, item) is None


def test_approval_still_publishes_when_there_is_nothing_to_place(client, db):
    item = _submission(db, classification={"summary": "", "concepts": []})

    research = approve_submission(db, item, LinkReview())

    assert item.review_status == "approved"
    assert research.status == "approved"


def test_the_same_submission_is_never_proposed_twice(client, db):
    item = _submission(db)

    first = create_link_change_set(db, item)
    db.commit()
    second = create_link_change_set(db, item)

    assert first.id == second.id


def test_placement_routes_to_a_matching_pillar_and_falls_back_to_the_root(client, db):
    ensure_seed_ontology(db)

    routed = resolve_parent_id(
        db,
        "Vector memory and retrieval for agents",
        "The system stores embeddings and retrieves prior context from a knowledge base.",
    )
    unroutable = resolve_parent_id(db, "zzz", "qqq")

    assert db.get(KnowledgeNode, routed).node_type in {"SystemPillar", "SystemRoot"}
    assert unroutable == ontology_id(ROOT_KEY)


def change_set_mutations(db, change_set_id: str) -> list[GraphMutation]:
    return list(
        db.scalars(
            select(GraphMutation)
            .where(GraphMutation.change_set_id == change_set_id)
            .order_by(GraphMutation.mutation_order)
        )
    )
