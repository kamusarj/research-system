import httpx
from fastapi.testclient import TestClient

from app import ollama_bridge


def test_bridge_only_exposes_bounded_ollama_routes(monkeypatch):
    async def fake_forward(method: str, path: str, body: bytes) -> httpx.Response:
        assert method == "GET"
        assert path == "api/tags"
        assert body == b""
        return httpx.Response(200, json={"models": [{"name": "local-test"}]})

    monkeypatch.setattr(ollama_bridge, "forward", fake_forward)
    client = TestClient(ollama_bridge.app)

    response = client.get("/api/tags")
    assert response.status_code == 200
    assert response.json()["models"][0]["name"] == "local-test"
    assert client.post("/api/pull", json={"name": "remote-model"}).status_code == 404


def test_bridge_rejects_oversized_requests(monkeypatch):
    monkeypatch.setattr(ollama_bridge, "MAX_REQUEST_BYTES", 4)
    response = TestClient(ollama_bridge.app).post("/api/generate", content=b"12345")
    assert response.status_code == 413
