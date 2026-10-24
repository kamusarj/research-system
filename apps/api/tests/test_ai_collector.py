from types import SimpleNamespace

from pydantic import BaseModel, SecretStr
from test_research import create_item

from app.core.config import settings
from app.models import AIOutput, EmbeddingChunk, Evaluation
from app.services.ai import DeepSeekProvider, MistralProvider, OllamaProvider, OpenAIProvider


class StructuredProbe(BaseModel):
    label: str


def test_ollama_provider_disables_thinking_and_sends_schema(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": '{"label":"local"}'}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr("app.services.ai.httpx.post", fake_post)

    result = OllamaProvider().complete_json("Return a label.", StructuredProbe)

    assert result.label == "local"
    assert captured["url"].endswith("/api/generate")
    assert captured["json"]["think"] is False
    assert captured["json"]["options"]["temperature"] == 0
    assert "label" in captured["json"]["format"]["properties"]


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


def test_openai_responses_disables_storage_and_uses_text_format(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"output_text": '{"label":"openai"}'}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr("app.services.ai.httpx.post", fake_post)
    monkeypatch.setattr(settings, "openai_api_key", SecretStr("unit-test-key"))

    result = OpenAIProvider().complete_json("Return a label.", StructuredProbe)

    assert result.label == "openai"
    assert captured["url"] == "https://api.openai.com/v1/responses"
    assert captured["json"]["store"] is False
    assert captured["json"]["text"]["format"]["type"] == "json_schema"
    assert captured["json"]["text"]["format"]["strict"] is True


def test_deepseek_provider_uses_json_mode_with_the_requested_schema(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": '{"label":"deepseek"}'}}]}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr("app.services.ai.httpx.post", fake_post)
    monkeypatch.setattr(DeepSeekProvider, "api_key", SecretStr("unit-test-key"))

    result = DeepSeekProvider().complete_json("Return a JSON label.", StructuredProbe)

    assert result.label == "deepseek"
    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert captured["json"]["model"] == DeepSeekProvider.model
    assert '"label"' in captured["json"]["messages"][1]["content"]


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
    monkeypatch.setattr("app.services.collector.fetch_feed", lambda _: feed)
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
