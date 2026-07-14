from app.models import LinkSubmission
from app.services.ingestion import run_pending_submissions


def test_provider_registry_never_exposes_keys(client):
    response = client.get("/api/v1/ai/providers")
    assert response.status_code == 200
    providers = response.json()
    assert {item["id"] for item in providers} == {
        "mock",
        "ollama",
        "openai",
        "deepseek",
        "gemini",
        "openrouter",
        "mistral",
    }
    assert all("api_key" not in item for item in providers)
    assert next(item for item in providers if item["id"] == "mistral")["configured"] is False


def test_link_intake_review_publish_and_typed_graph(client, db, monkeypatch):
    content = (
        "A LangGraph RAG agent helps customer service teams retrieve policies and automate "
        "repeatable support workflows with human approval and measurable operations outcomes."
    )
    monkeypatch.setattr(
        "app.services.ingestion.fetch_url",
        lambda _: ("https://example.com/langgraph-agent", "LangGraph support agent", content),
    )
    response = client.post(
        "/api/v1/ingestion/links",
        json={"url": "https://example.com/langgraph-agent", "provider": "mock"},
    )
    assert response.status_code == 202, response.text
    submission = response.json()
    assert submission["status"] == "queued"

    assert run_pending_submissions(db) == 1
    submission = client.get("/api/v1/ingestion/links").json()[0]
    assert submission["status"] == "needs-review"
    assert submission["attempt_count"] == 1
    assert submission["classification"]["confidence"] == 0.65
    assert "LangGraph" in submission["classification"]["technologies"]

    approved = client.post(
        f"/api/v1/ingestion/links/{submission['id']}/approve", json={}
    )
    assert approved.status_code == 200
    research_id = approved.json()["research_id"]
    research = client.get(f"/api/v1/research/{research_id}").json()
    assert research["status"] == "approved"
    assert research["metadata"]["link_submission_id"] == submission["id"]

    graph = client.get("/api/v1/graph").json()
    assert any(
        node["type"] == "Technology" and node["label"] == "LangGraph"
        for node in graph["nodes"]
    )
    assert any(edge["type"] == "USES_TECH" for edge in graph["edges"])
    stats = client.get("/api/v1/graph/stats").json()
    assert stats["by_type"]["Technology"] >= 1
    assert client.get("/api/v1/graph/clusters").status_code == 200

    duplicate = client.post(
        "/api/v1/ingestion/links", json={"url": "https://example.com/langgraph-agent"}
    )
    assert duplicate.status_code == 200
    assert db.query(LinkSubmission).count() == 1


def test_private_url_is_queued_without_fetching_in_request(client):
    response = client.post("/api/v1/ingestion/links", json={"url": "http://127.0.0.1/admin"})
    assert response.status_code == 202
    assert response.json()["status"] == "queued"


def test_private_url_moves_directly_to_dead_letter(client, db):
    response = client.post("/api/v1/ingestion/links", json={"url": "http://127.0.0.1/admin"})
    submission_id = response.json()["id"]

    assert run_pending_submissions(db) == 1
    submission = client.get("/api/v1/ingestion/links").json()[0]
    assert submission["status"] == "dead-letter"
    assert submission["attempt_count"] == 1
    assert "not allowed" in submission["error"]

    retried = client.post(f"/api/v1/ingestion/links/{submission_id}/retry")
    assert retried.status_code == 200
    assert retried.json()["status"] == "queued"
    assert retried.json()["attempt_count"] == 0


def test_resubmitting_dead_letter_url_requeues_with_selected_provider(client, db):
    url = "http://127.0.0.1/resubmit"
    original = client.post(
        "/api/v1/ingestion/links", json={"url": url, "provider": "openrouter"}
    )
    assert run_pending_submissions(db) == 1
    failed = db.get(LinkSubmission, original.json()["id"])
    assert failed.status == "dead-letter"
    assert failed.provider_name == "openrouter"

    resubmitted = client.post(
        "/api/v1/ingestion/links", json={"url": url, "provider": "deepseek"}
    )

    assert resubmitted.status_code == 202
    assert resubmitted.json()["id"] == original.json()["id"]
    assert resubmitted.json()["status"] == "queued"
    assert resubmitted.json()["provider_name"] == "deepseek"
    assert resubmitted.json()["attempt_count"] == 0
    assert db.query(LinkSubmission).count() == 1


def test_transient_failure_retries_then_succeeds(client, db, monkeypatch):
    attempts = 0
    content = "Reliable business agent research content with enough detail. " * 3

    def flaky_fetch(_: str) -> tuple[str, str, str]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("temporary network failure")
        return "https://example.com/retry", "Retry succeeds", content

    monkeypatch.setattr("app.services.ingestion.fetch_url", flaky_fetch)
    monkeypatch.setattr("app.services.ingestion.settings.intake_retry_base_seconds", 0)
    response = client.post(
        "/api/v1/ingestion/links",
        json={"url": "https://example.com/retry", "provider": "mock"},
    )

    assert run_pending_submissions(db, max_jobs=1) == 1
    first = db.get(LinkSubmission, response.json()["id"])
    assert first.status == "retrying"
    assert first.attempt_count == 1

    assert run_pending_submissions(db, max_jobs=1) == 1
    db.refresh(first)
    assert first.status == "needs-review"
    assert first.attempt_count == 2
