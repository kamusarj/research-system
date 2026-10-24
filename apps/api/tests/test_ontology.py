from sqlalchemy import func, select

from app.models import KnowledgeNode
from app.services.ontology import ROOT_KEY, ensure_seed_ontology, ontology_id, validate_placement


def test_seed_ontology_is_idempotent_and_has_eleven_pillars(db):
    ensure_seed_ontology(db)
    ensure_seed_ontology(db)

    assert db.scalar(select(func.count()).select_from(KnowledgeNode)) == 12
    root = db.get(KnowledgeNode, ontology_id(ROOT_KEY))
    assert root is not None
    assert root.primary_parent_id is None
    assert (
        db.scalar(
            select(func.count())
            .select_from(KnowledgeNode)
            .where(KnowledgeNode.primary_parent_id == root.id)
        )
        == 11
    )


def test_ontology_api_and_hierarchy_graph(client, db):
    ensure_seed_ontology(db)

    ontology = client.get("/api/v1/ontology")
    assert ontology.status_code == 200
    payload = ontology.json()
    assert len(payload["nodes"]) == 12
    assert len(payload["edges"]) == 11
    assert payload["root_ids"] == [ontology_id(ROOT_KEY)]

    root_id = payload["root_ids"][0]
    root = next(node for node in payload["nodes"] if node["id"] == root_id)
    assert root["child_count"] == 11

    roots = client.get("/api/v1/ontology/roots")
    assert roots.status_code == 200
    assert [item["id"] for item in roots.json()] == [root_id]

    children = client.get(f"/api/v1/ontology/nodes/{root_id}/children")
    assert children.status_code == 200
    assert len(children.json()) == 11

    pillar_id = children.json()[0]["id"]
    breadcrumb = client.get(f"/api/v1/ontology/nodes/{pillar_id}/breadcrumb")
    assert breadcrumb.status_code == 200
    assert [item["id"] for item in breadcrumb.json()] == [root_id, pillar_id]

    system_map = client.get("/api/v1/graph/system", params={"limit": 40})
    assert system_map.status_code == 200
    graph = system_map.json()
    assert graph["meta"]["view"] == "hierarchy"
    assert graph["meta"]["provider"] == "postgres-system"
    assert len(graph["nodes"]) == 12
    assert len(graph["edges"]) == 11
    assert {edge["type"] for edge in graph["edges"]} == {"PARENT_OF"}

    knowledge_hierarchy = client.get("/api/v1/graph", params={"view": "hierarchy", "limit": 40})
    assert knowledge_hierarchy.status_code == 200
    assert knowledge_hierarchy.json()["nodes"] == []


def test_placement_validation_rejects_cycle(client, db):
    ensure_seed_ontology(db)
    root_id = ontology_id(ROOT_KEY)
    pillar_id = ontology_id("business-context")

    assert validate_placement(db, pillar_id, root_id) == [
        "Placement would create a hierarchy cycle"
    ]

    response = client.post(
        "/api/v1/ontology/validate-placement",
        json={"parent_id": pillar_id, "node_id": root_id},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["errors"] == ["Placement would create a hierarchy cycle"]


def test_ontology_searches_english_and_vietnamese_labels(client, db):
    ensure_seed_ontology(db)

    english = client.get("/api/v1/ontology/search", params={"q": "architecture"})
    vietnamese = client.get("/api/v1/ontology/search", params={"q": "quản trị"})

    assert english.status_code == 200
    assert english.json()[0]["normalized_key"] == "agent-system-architecture"
    assert vietnamese.status_code == 200
    assert vietnamese.json()[0]["normalized_key"] == "evaluation-risk-governance"
