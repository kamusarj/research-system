from test_research import create_item

from app.api.search import search_statement
from app.schemas.graph import GraphQuery
from app.services.graph import filter_graph


def test_search_uses_exists_instead_of_distinct_over_json_columns():
    sql = str(search_statement("rag"))
    assert "DISTINCT" not in sql
    assert "EXISTS" in sql


def test_relationship_projection_is_not_capped_at_one_hundred_nodes():
    projection = {
        "nodes": [
            {"id": f"node:{index}", "type": "Concept", "label": f"Concept {index}"}
            for index in range(150)
        ],
        "edges": [],
    }

    response = filter_graph(projection, GraphQuery(limit=1000), "postgres")

    assert response.meta.node_count == 150
    assert response.meta.truncated is False


def approve(client, item):
    client.post(f"/api/v1/research/{item['id']}/submit-review")
    return client.post(f"/api/v1/research/{item['id']}/approve").json()


def test_approved_research_search_related_and_graph(client):
    memory = approve(client, create_item(client, "Durable Agent Memory", ["Memory", "RAG"]))
    tools = approve(client, create_item(client, "Business Tool Use", ["RAG", "Tools"]))
    draft = create_item(client, "Draft RAG Notes", ["RAG"])
    client.post(
        f"/api/v1/research/{memory['id']}/relations",
        json={"target_id": tools["id"], "relation_type": "supports"},
    )

    results = client.get("/api/v1/search?q=rag").json()
    assert results["total"] == 2
    assert draft["id"] not in {item["id"] for item in results["items"]}
    related = client.get(f"/api/v1/research/{memory['id']}/related").json()
    assert tools["id"] in {item["id"] for item in related}

    graph = client.get("/api/v1/graph").json()
    assert memory["id"] in {node["id"] for node in graph["nodes"]}
    assert "tag:rag" in {node["id"] for node in graph["nodes"]}
    assert any(edge["type"] == "SUPPORTS" for edge in graph["edges"])
    hierarchy = client.get("/api/v1/graph", params={"view": "hierarchy", "limit": 1000}).json()
    assert {node["id"] for node in hierarchy["nodes"]} == {node["id"] for node in graph["nodes"]}
    assert any(
        edge["source"] == "tag:rag" and edge["target"] in {memory["id"], tools["id"]}
        for edge in hierarchy["edges"]
    )
    ego = client.get(f"/api/v1/graph/ego/{memory['id']}")
    assert ego.status_code == 200
    path = client.get("/api/v1/graph/path", params={"from": memory["id"], "to": tools["id"]})
    assert path.status_code == 200
