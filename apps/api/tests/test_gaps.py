from test_research import create_item


def approve(client, item):
    client.post(f"/api/v1/research/{item['id']}/submit-review")
    return client.post(f"/api/v1/research/{item['id']}/approve").json()


def test_detect_assign_and_fill_gap_with_human_approved_deep_research(client):
    approve(client, create_item(client, "Sparse Agent Evaluation", ["Evaluation"]))
    gaps = client.post("/api/v1/gaps/detect").json()
    gap = next(item for item in gaps if item["concept_key"] == "evaluation")
    assert gap["status"] == "detected"
    assert gap["coverage_count"] == 1

    assigned = client.post(
        f"/api/v1/gaps/{gap['id']}/assign", json={"assigned_to": "Research team"}
    ).json()
    assert assigned["status"] == "assigned"

    report_response = client.post(f"/api/v1/gaps/{gap['id']}/request-deep-research")
    assert report_response.status_code == 201
    report = report_response.json()
    assert report["type"] == "deep-research-report"
    assert report["status"] == "draft"
    assert report["metadata"]["human_approval_required"] is True

    blocked = client.post(f"/api/v1/deep-research/{report['id']}/approve")
    assert blocked.status_code == 409
    client.post(f"/api/v1/research/{report['id']}/submit-review")
    approved = client.post(f"/api/v1/deep-research/{report['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    current = client.get("/api/v1/gaps").json()
    assert next(item for item in current if item["id"] == gap["id"])["status"] == "filled"


def test_dismissed_gap_is_not_reopened_by_detection(client):
    approve(client, create_item(client, "Agent Memory Note", ["Memory"]))
    client.post("/api/v1/gaps/detect")
    gap = client.get("/api/v1/graph/gaps").json()[0]
    dismissed = client.post(
        f"/api/v1/gaps/{gap['id']}/dismiss", json={"reason": "Covered elsewhere"}
    )
    assert dismissed.status_code == 200
    assert dismissed.json()["status"] == "dismissed"
    detected_again = client.post("/api/v1/gaps/detect").json()
    assert next(item for item in detected_again if item["id"] == gap["id"])["status"] == "dismissed"
