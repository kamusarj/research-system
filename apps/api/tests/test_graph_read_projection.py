from app.core.config import settings
from app.models import KnowledgeEdge, KnowledgeNode, NodeEvidence
from app.services.ontology import ensure_seed_ontology, ontology_id


def _node(label, *, primary_parent_id=None, node_type="Concept", status="approved"):
    return KnowledgeNode(
        id=label,
        canonical_label=label,
        normalized_key=label.casefold(),
        node_type=node_type,
        primary_parent_id=primary_parent_id,
        lifecycle_status=status,
        description="Graph read fixture.",
    )


def _edge(edge_id, parent, child, *, edge_type="PARENT_OF", status="approved"):
    return KnowledgeEdge(
        id=edge_id,
        source_node_id=parent,
        target_node_id=child,
        edge_type=edge_type,
        confidence=0.9,
        lifecycle_status=status,
    )


def test_graph_includes_only_the_approved_canonical_edge_evidence(client, db):
    db.add_all([_node("Parent"), _node("Child"), _node("Draft", status="draft")])
    db.flush()
    db.add_all(
        [
            _edge("published", "Parent", "Child", edge_type="RELATED_TO"),
            _edge("archived", "Parent", "Child", status="archived"),
            _edge("unpublished-endpoint", "Parent", "Draft"),
            NodeEvidence(
                owner_kind="knowledge_edge",
                owner_id="published",
                excerpt="Published evidence.",
                location={"section_heading": "Results", "page": 3, "internal_path": "/private"},
                provenance={"change_set_id": "internal-id"},
            ),
            NodeEvidence(
                owner_kind="document_edge", owner_id="published", excerpt="Document draft"
            ),
            NodeEvidence(
                owner_kind="knowledge_edge", owner_id="archived", excerpt="Archived evidence"
            ),
        ]
    )
    db.commit()

    result = client.get("/api/v1/graph").json()

    assert {edge["id"] for edge in result["edges"]} == {"published"}
    [edge] = result["edges"]
    assert edge["evidence_count"] == 1
    assert edge["evidence"] == [{"text": "Published evidence.", "section": "Results", "page": 3}]


def test_hierarchy_keeps_evidenced_structural_edges_without_adding_display_parents(client, db):
    db.add_all(
        [
            _node("Preferred"),
            _node("Alternative"),
            _node("Child", primary_parent_id="Preferred"),
            _node("Leaf"),
        ]
    )
    db.flush()
    db.add_all(
        [
            _edge("primary-broader", "Preferred", "Child", edge_type="BROADER_THAN"),
            _edge("secondary-parent", "Alternative", "Child"),
            _edge("back-edge", "Child", "Preferred"),
            _edge("leaf-parent", "Child", "Leaf"),
            NodeEvidence(
                owner_kind="knowledge_edge",
                owner_id="primary-broader",
                excerpt="Approved hierarchy.",
            ),
        ]
    )
    db.commit()

    result = client.get("/api/v1/graph", params={"view": "hierarchy"}).json()
    nodes = {node["id"]: node for node in result["nodes"]}
    edges = {edge["id"]: edge for edge in result["edges"]}

    assert nodes["Preferred"]["primary_parent_id"] is None
    assert nodes["Child"]["primary_parent_id"] == "Preferred"
    assert nodes["Leaf"]["primary_parent_id"] == "Child"
    assert nodes["Alternative"]["child_count"] == 0
    assert set(edges) == {"primary-broader", "secondary-parent", "back-edge", "leaf-parent"}
    assert edges["primary-broader"]["type"] == "BROADER_THAN"
    assert edges["primary-broader"]["hierarchy_secondary"] is False
    assert edges["primary-broader"]["evidence"] == [{"text": "Approved hierarchy."}]
    assert edges["secondary-parent"]["hierarchy_secondary"] is True
    assert edges["back-edge"]["hierarchy_secondary"] is True

    branch = client.get(
        "/api/v1/graph",
        params={
            "view": "hierarchy",
            "root_node_id": "Alternative",
            "depth": 2,
        },
    ).json()
    assert {node["id"] for node in branch["nodes"]} == {"Alternative"}


def test_system_children_include_broader_than_without_counting_duplicate_pairs(client, db):
    ensure_seed_ontology(db)
    pillar_id = ontology_id("agent-system-architecture")
    db.add_all([_node("Broader child"), _node("Two edge kinds")])
    db.flush()
    db.add_all(
        [
            _edge("only-broader", pillar_id, "Broader child", edge_type="BROADER_THAN"),
            _edge("both-parent", pillar_id, "Two edge kinds"),
            _edge("both-broader", pillar_id, "Two edge kinds", edge_type="BROADER_THAN"),
        ]
    )
    db.commit()

    graph = client.get("/api/v1/graph/system").json()
    nodes = {node["id"]: node for node in graph["nodes"]}
    edges = {edge["id"]: edge for edge in graph["edges"]}
    assert nodes[pillar_id]["child_count"] == 2
    assert nodes["Broader child"]["primary_parent_id"] == pillar_id
    assert edges["only-broader"]["hierarchy_secondary"] is False
    assert edges["both-broader"]["hierarchy_secondary"] is True


def test_full_graph_uses_the_configured_cap_without_replacing_existing_default(client, monkeypatch):
    monkeypatch.setattr(settings, "graph_default_node_limit", 40)
    monkeypatch.setattr(settings, "graph_max_node_limit", 75)

    assert client.get("/api/v1/graph").json()["meta"]["node_limit"] == 40
    assert client.get("/api/v1/graph", params={"full": True}).json()["meta"]["node_limit"] == 75
    assert client.get("/api/v1/graph/system").json()["meta"]["node_limit"] == 75
    explicit = client.get("/api/v1/graph", params={"full": True, "limit": 20})
    assert explicit.json()["meta"]["node_limit"] == 20

    monkeypatch.setattr(settings, "graph_max_node_limit", 10)
    assert client.get("/api/v1/graph").json()["meta"]["node_limit"] == 10


def test_neighbor_expansion_respects_the_active_node_filter(client, db):
    db.add_all([_node("Root"), _node("Allowed"), _node("Technology", node_type="Technology")])
    db.flush()
    db.add_all([_edge("matching", "Root", "Allowed"), _edge("excluded", "Root", "Technology")])
    db.commit()

    neighbors = client.get("/api/v1/graph/nodes/Root/neighbors").json()
    assert {node["id"] for node in neighbors["nodes"]} == {"Root", "Allowed", "Technology"}
    filtered = client.get(
        "/api/v1/graph/nodes/Root/neighbors", params={"node_types": "Concept"}
    ).json()
    assert {node["id"] for node in filtered["nodes"]} == {"Root", "Allowed"}
    assert {edge["id"] for edge in filtered["edges"]} == {"matching"}
