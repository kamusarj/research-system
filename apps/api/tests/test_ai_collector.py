from types import SimpleNamespace

from pydantic import BaseModel, SecretStr
from test_research import create_item

from app.models import AIOutput, EmbeddingChunk, Evaluation
from app.services.ai import MistralProvider


class StructuredProbe(BaseModel):
    label: str


def test_mistral_provider_uses_strict_json_schema(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": '{"label":"ok"}'}}]}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr("app.services.ai.httpx.post", fake_post)
    monkeypatch.setattr(MistralProvider, "api_key", SecretStr("unit-test-key"))

    result = MistralProvider().complete_json("Return a label.", StructuredProbe)

    assert result.label == "ok"
    assert captured["url"] == "https://api.mistral.ai/v1/chat/completions"
    response_format = captured["json"]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert "label" in response_format["json_schema"]["schema"]["properties"]


def test_ai_enrichment_preserves_human_fields_until_accepted(client, db):
    item = create_item(client, "RAG Agent", ["Human Tag"])
    response = client.post(f"/api/v1/ai/enrich/{item['id']}")
    assert response.status_code == 200
    suggestion = response.json()
    unchanged = client.get(f"/api/v1/research/{item['id']}").json()
    assert unchanged["summary"] is None
    assert unchanged["tags"] == ["Human Tag"]
    assert db.query(AIOutput).count() == 1
    assert db.query(EmbeddingChunk).count() == 1
    accepted = client.post(f"/api/v1/ai/outputs/{suggestion['id']}/accept")
    assert accepted.status_code == 200
    assert accepted.json()["summary"]


def test_rss_collector_routes_review_items(client, db, monkeypatch):
    feed = SimpleNamespace(
        bozo=False,
        entries=[
            {
                "id": "entry-1",
                "link": "https://example.com/agent",
                "title": "AI agent field note",
                "summary": "A short note about an AI agent.",
                "authors": [{"name": "Researcher"}],
            }
        ],
    )
    monkeypatch.setattr("app.services.collector.feedparser.parse", lambda _: feed)
    source = client.post(
        "/api/v1/collector/sources",
        json={
            "key": "example-feed",
            "name": "Example feed",
            "type": "rss",
            "url": "https://example.com/feed.xml",
            "auto_approve_threshold": 100,
            "auto_reject_threshold": 0,
        },
    )
    assert source.status_code == 201, source.text
    run = client.post(f"/api/v1/collector/sources/{source.json()['id']}/run")
    assert run.json()["status"] == "completed"
    queue = client.get("/api/v1/collector/review-queue").json()
    assert len(queue) == 1
    approved = client.post(f"/api/v1/collector/review-queue/{queue[0]['id']}/approve")
    assert approved.status_code == 200
    research = client.get(f"/api/v1/research/{approved.json()['research_id']}").json()
    assert research["status"] == "approved"
    assert research["collection_method"] == "auto-collected"
    assert db.query(Evaluation).count() == 1
