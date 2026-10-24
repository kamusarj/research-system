"""One concept should be one node, whichever graph view you are looking at.

The relationship view builds taxonomy nodes from free-text classifier output; the
hierarchy view reads canonical ontology records. Without reconciliation the same idea
appears twice under two unrelated IDs, so selecting it in one view loses it in the other
and the node counts overstate what the system actually knows.
"""

from app.models import ConceptAlias, KnowledgeNode, ResearchItem
from app.services.graph import canonical_node_index, graph_projection, ontology_graph_projection
from app.services.ontology import ensure_seed_ontology, normalize_ontology_key


def _canonical(db, label: str, node_type: str = "Technology") -> KnowledgeNode:
    root = ensure_seed_ontology(db)[0]
    node = KnowledgeNode(
        node_type=node_type,
        canonical_label=label,
        normalized_key=normalize_ontology_key(label),
        description=f"The canonical record for {label}.",
        primary_parent_id=root.id,
        lifecycle_status="approved",
        created_by_type="test",
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


def _approved_research(db, *, technologies: list[str]) -> ResearchItem:
    item = ResearchItem(
        title="Vector memory for agents",
        type="reference",
        collection_method="auto-collected",
        status="approved",
        summary="A grounded report.",
        content="A grounded report about vector memory.",
        metadata_json={"classification": {"technologies": technologies, "confidence": 0.9}},
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def test_a_classified_label_adopts_the_canonical_node_identity(client, db):
    canonical = _canonical(db, "pgvector")
    _approved_research(db, technologies=["pgvector"])

    relationship = graph_projection(db)
    hierarchy = ontology_graph_projection(db)
    relationship_ids = {node["id"] for node in relationship["nodes"]}
    hierarchy_ids = {node["id"] for node in hierarchy["nodes"]}

    assert canonical.id in relationship_ids
    # The same ID in both views is what lets a selection survive switching between them.
    assert canonical.id in hierarchy_ids
    assert "technology:pgvector" not in relationship_ids


def test_a_differently_worded_label_matches_through_its_alias(client, db):
    canonical = _canonical(db, "pgvector")
    db.add(
        ConceptAlias(
            knowledge_node_id=canonical.id,
            alias="Postgres vector extension",
            normalized_alias=normalize_ontology_key("Postgres vector extension"),
            language="en",
            alias_type="synonym",
            lifecycle_status="approved",
            created_by_type="test",
        )
    )
    db.commit()
    _approved_research(db, technologies=["Postgres vector extension"])

    projected = {node["id"]: node for node in graph_projection(db)["nodes"]}

    assert canonical.id in projected
    node = projected[canonical.id]
    assert node["label"] == "pgvector"
    # The classifier's wording is kept, so a reviewer can see why the match was made.
    assert "Postgres vector extension" in node["aliases"]


def test_two_wordings_of_one_concept_collapse_into_a_single_node(client, db):
    canonical = _canonical(db, "pgvector")
    db.add(
        ConceptAlias(
            knowledge_node_id=canonical.id,
            alias="PGVector",
            normalized_alias=normalize_ontology_key("PGVector"),
            language="en",
            alias_type="synonym",
            lifecycle_status="approved",
            created_by_type="test",
        )
    )
    db.commit()
    _approved_research(db, technologies=["pgvector", "PGVector"])

    technology_nodes = [
        node for node in graph_projection(db)["nodes"] if node["type"] == "Technology"
    ]

    assert len(technology_nodes) == 1
    assert technology_nodes[0]["source_count"] == 2


def test_an_unmatched_label_still_appears_under_its_derived_key(client, db):
    ensure_seed_ontology(db)
    _approved_research(db, technologies=["a technology nobody has catalogued"])

    projected = {node["id"]: node for node in graph_projection(db)["nodes"]}
    derived = projected["technology:a-technology-nobody-has-catalogued"]

    # Not yet canonical is not the same as invisible: it stays browsable and reviewable.
    assert derived["label"] == "a technology nobody has catalogued"
    assert derived["canonical_node_id"] is None


def test_the_index_prefers_a_canonical_label_over_a_colliding_alias(client, db):
    exact = _canonical(db, "pgvector")
    other = _canonical(db, "Timescale")
    db.add(
        ConceptAlias(
            knowledge_node_id=other.id,
            alias="pgvector",
            normalized_alias=normalize_ontology_key("pgvector"),
            language="en",
            alias_type="synonym",
            lifecycle_status="approved",
            created_by_type="test",
        )
    )
    db.commit()

    index = canonical_node_index(db)

    assert index[("Technology", "pgvector")].id == exact.id
