from test_research import create_item


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
    ego = client.get(f"/api/v1/graph/ego/{memory['id']}")
    assert ego.status_code == 200
    path = client.get("/api/v1/graph/path", params={"from": memory["id"], "to": tools["id"]})
    assert path.status_code == 200
