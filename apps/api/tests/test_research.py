def create_item(client, title="Agent Memory", tags=None):
    response = client.post(
        "/api/v1/research",
        json={
            "title": title,
            "type": "internal-research",
            "collection_method": "manual",
            "content": "Research on durable memory.",
            "tags": tags or ["Agent Memory"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_research_lifecycle_version_and_archive(client):
    item = create_item(client)
    assert item["display_id"].startswith("RES-")
    assert item["tags"] == ["Agent Memory"]

    updated = client.put(
        f"/api/v1/research/{item['id']}",
        json={"summary": "A human-authored summary", "tags": ["Memory", "RAG"]},
    )
    assert updated.status_code == 200
    versions = client.get(f"/api/v1/research/{item['id']}/versions").json()
    assert versions[0]["snapshot"]["summary"] is None
    assert versions[0]["version_number"] == 1

    assert (
        client.post(f"/api/v1/research/{item['id']}/submit-review").json()["status"] == "in-review"
    )
    assert client.post(f"/api/v1/research/{item['id']}/approve").json()["status"] == "approved"
    assert client.post(f"/api/v1/research/{item['id']}/approve").status_code == 409
    assert client.delete(f"/api/v1/research/{item['id']}").status_code == 204
    assert client.get("/api/v1/research").json()["total"] == 0


def test_relations_comments_and_filters(client):
    source = create_item(client, "Source", ["RAG"])
    target = create_item(client, "Target", ["Tools"])
    relation = client.post(
        f"/api/v1/research/{source['id']}/relations",
        json={"target_id": target["id"], "relation_type": "extends"},
    )
    assert relation.status_code == 201
    assert len(client.get(f"/api/v1/research/{source['id']}/relations").json()) == 1

    comment = client.post(
        f"/api/v1/research/{source['id']}/comments",
        json={"body": "Please add evidence.", "author": "Reviewer"},
    )
    assert comment.status_code == 201
    assert client.get(f"/api/v1/research/{source['id']}/comments").json()[0]["author"] == "Reviewer"
    assert client.get("/api/v1/research?tag=rag").json()["total"] == 1

    attachment = client.post(
        f"/api/v1/research/{source['id']}/attachments",
        json={
            "filename": "notes.pdf",
            "object_key": f"research/{source['id']}/notes.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 1200,
        },
    )
    assert attachment.status_code == 201
    assert (
        client.get(f"/api/v1/research/{source['id']}/attachments").json()[0]["filename"]
        == "notes.pdf"
    )


def test_structured_error_format(client):
    response = client.get("/api/v1/research/not-found")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SOURCE_NOT_FOUND"


def test_reviewer_can_reject_and_resubmit_research(client):
    item = create_item(client, "Review workflow")
    client.post(f"/api/v1/research/{item['id']}/submit-review")

    rejected = client.post(f"/api/v1/research/{item['id']}/reject")
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    resubmitted = client.post(f"/api/v1/research/{item['id']}/submit-review")
    assert resubmitted.status_code == 200
    assert resubmitted.json()["status"] == "in-review"
