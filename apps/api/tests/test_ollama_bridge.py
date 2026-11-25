import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app import ollama_bridge


@pytest.fixture(autouse=True)
def isolated_bridge(monkeypatch):
    monkeypatch.setattr(ollama_bridge, "PROTOCOL", "ollama")
    monkeypatch.setattr(ollama_bridge, "UPSTREAM", "http://model.internal:11434")
    monkeypatch.setattr(ollama_bridge, "MAX_REQUEST_BYTES", 2_000_000)
    monkeypatch.setattr(ollama_bridge, "MAX_RESPONSE_BYTES", 2_000_000)
    monkeypatch.setattr(ollama_bridge, "WALL_TIMEOUT_SECONDS", 130)


def use_transport(monkeypatch, handler):
    real_client = httpx.AsyncClient
    options = []

    def client(**kwargs):
        options.append(kwargs)
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(ollama_bridge.httpx, "AsyncClient", client)
    return options


@pytest.mark.parametrize(
    ("protocol", "method", "path"),
    [
        ("ollama", "GET", "/api/tags"),
        ("ollama", "GET", "/api/version"),
        ("ollama", "POST", "/api/generate"),
        ("ollama", "POST", "/api/chat"),
        ("openai_compatible", "GET", "/v1/models"),
        ("openai_compatible", "POST", "/v1/chat/completions"),
    ],
)
def test_bridge_allows_only_inference_and_inventory(monkeypatch, protocol, method, path):
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(ollama_bridge, "PROTOCOL", protocol)
    use_transport(monkeypatch, handler)
    response = TestClient(ollama_bridge.app).request(method, path)
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert str(requests[0].url) == f"http://model.internal:11434{path}"


@pytest.mark.parametrize(
    ("protocol", "method", "path"),
    [
        ("ollama", "POST", "/api/pull"),
        ("ollama", "POST", "/api/delete"),
        ("ollama", "POST", "/api/create"),
        ("ollama", "GET", "/v1/models"),
        ("ollama", "POST", "/api/tags"),
        ("ollama", "GET", "/api/generate"),
        ("openai_compatible", "GET", "/api/tags"),
        ("openai_compatible", "POST", "/v1/files"),
        ("openai_compatible", "POST", "/v1/responses"),
        ("openai_compatible", "GET", "/http://elsewhere.internal/v1/models"),
    ],
)
def test_bridge_denies_other_routes_without_contacting_upstream(
    monkeypatch, protocol, method, path
):
    async def unexpected(*_args):
        raise AssertionError("Disallowed route reached upstream")

    monkeypatch.setattr(ollama_bridge, "PROTOCOL", protocol)
    monkeypatch.setattr(ollama_bridge, "forward", unexpected)
    assert TestClient(ollama_bridge.app).request(method, path).status_code == 404


def test_bridge_uses_only_fixed_origin_and_bearer_header(monkeypatch):
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"models": []})

    options = use_transport(monkeypatch, handler)
    response = TestClient(ollama_bridge.app).get(
        "/api/tags?url=http://elsewhere.internal&key=caller",
        headers={
            "Authorization": "Bearer test-key",
            "Cookie": "session=caller",
            "X-Api-Key": "caller",
            "X-Forwarded-Host": "elsewhere.internal",
        },
    )
    assert response.status_code == 200
    assert str(requests[0].url) == "http://model.internal:11434/api/tags"
    assert requests[0].headers["Authorization"] == "Bearer test-key"
    for name in ("Cookie", "X-Api-Key", "X-Forwarded-Host"):
        assert name not in requests[0].headers
    assert options[0]["follow_redirects"] is False
    assert options[0]["trust_env"] is False


@pytest.mark.parametrize("authorization", ["Basic fixture", "Bearer ", "Bearer bad token"])
def test_bridge_rejects_unsupported_authorization(monkeypatch, authorization):
    async def unexpected(*_args):
        raise AssertionError("Invalid header reached upstream")

    monkeypatch.setattr(ollama_bridge, "forward", unexpected)
    response = TestClient(ollama_bridge.app).get(
        "/api/tags", headers={"Authorization": authorization}
    )
    assert response.status_code == 400
    assert authorization not in response.text


def test_bridge_rejects_oversized_requests_before_upstream(monkeypatch):
    async def unexpected(*_args):
        raise AssertionError("Oversized body reached upstream")

    monkeypatch.setattr(ollama_bridge, "MAX_REQUEST_BYTES", 4)
    monkeypatch.setattr(ollama_bridge, "forward", unexpected)
    assert TestClient(ollama_bridge.app).post("/api/generate", content=b"12345").status_code == 413


def test_bridge_stops_reading_chunked_input_at_limit(monkeypatch):
    monkeypatch.setattr(ollama_bridge, "MAX_REQUEST_BYTES", 4)
    received = []

    async def receive():
        received.append(True)
        return {"type": "http.request", "body": b"123", "more_body": True}

    request = Request({"type": "http", "headers": []}, receive=receive)
    with pytest.raises(ollama_bridge.HTTPException) as error:
        asyncio.run(ollama_bridge.bounded_body(request))
    assert error.value.status_code == 413
    assert len(received) == 2


class ChunkedResponse(httpx.AsyncByteStream):
    def __init__(self):
        self.read_chunks = 0

    async def __aiter__(self):
        for _ in range(20):
            self.read_chunks += 1
            yield b"123"


def test_bridge_stops_reading_response_at_limit(monkeypatch):
    stream = ChunkedResponse()

    async def handler(_request):
        return httpx.Response(200, headers={"content-type": "application/json"}, stream=stream)

    monkeypatch.setattr(ollama_bridge, "MAX_RESPONSE_BYTES", 4)
    use_transport(monkeypatch, handler)
    response = TestClient(ollama_bridge.app).get("/api/tags")
    assert response.status_code == 502
    assert stream.read_chunks < 20


def test_bridge_rejects_redirect_without_forwarding_key(monkeypatch):
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(307, headers={"location": "http://elsewhere.internal/private"})

    use_transport(monkeypatch, handler)
    response = TestClient(ollama_bridge.app).get(
        "/api/tags", headers={"Authorization": "Bearer test-key"}
    )
    assert response.status_code == 502
    assert len(requests) == 1
    assert requests[0].url.host == "model.internal"
    assert "location" not in response.headers
    assert "elsewhere.internal" not in response.text
    assert "test-key" not in response.text


@pytest.mark.parametrize("status", [401, 403, 404, 429, 503])
def test_bridge_sanitizes_upstream_errors(monkeypatch, status):
    async def handler(_request):
        return httpx.Response(status, json={"error": "private-upstream-details"})

    use_transport(monkeypatch, handler)
    response = TestClient(ollama_bridge.app).get("/api/tags")
    assert response.status_code == status
    assert "private-upstream-details" not in response.text


@pytest.mark.parametrize(
    "error_type, status", [(httpx.ConnectError, 502), (httpx.ReadTimeout, 504)]
)
def test_bridge_sanitizes_transport_failures(monkeypatch, error_type, status):
    async def handler(_request):
        raise error_type("private-upstream-details")

    use_transport(monkeypatch, handler)
    response = TestClient(ollama_bridge.app).get("/api/tags")
    assert response.status_code == status
    assert "private-upstream-details" not in response.text


def test_bridge_enforces_total_wall_deadline(monkeypatch):
    async def slow(*_args):
        await asyncio.sleep(0.1)

    monkeypatch.setattr(ollama_bridge, "WALL_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(ollama_bridge, "forward", slow)
    assert TestClient(ollama_bridge.app).get("/api/tags").status_code == 504


@pytest.mark.parametrize(
    "upstream",
    [
        "file:///tmp/model",
        "http://user:fixture@model.internal",
        "http://model.internal/v1",
        "http://model.internal/?key=fixture",
        "http://model.internal/#fragment",
        "http://model.internal:\n11434",
    ],
)
def test_bridge_refuses_invalid_config_without_echoing_it(monkeypatch, upstream):
    monkeypatch.setattr(ollama_bridge, "UPSTREAM", upstream)
    response = TestClient(ollama_bridge.app).get("/api/tags")
    assert response.status_code == 503
    assert upstream not in response.text


@pytest.mark.parametrize("headers", [{"content-type": "text/html"}, {"content-encoding": "gzip"}])
def test_bridge_rejects_non_json_or_compressed_response(monkeypatch, headers):
    async def handler(_request):
        return httpx.Response(200, headers=headers, stream=ChunkedResponse())

    use_transport(monkeypatch, handler)
    assert TestClient(ollama_bridge.app).get("/api/tags").status_code == 502


@pytest.mark.parametrize("team", [False, True])
def test_local_model_compose_preserves_config_and_private_bridges(tmp_path, team):
    if not shutil.which("docker"):
        pytest.skip("Docker Compose is not installed")
    if subprocess.run(["docker", "compose", "version"], capture_output=True).returncode:
        pytest.skip("Docker Compose is not installed")
    root = Path(__file__).resolve().parents[3]
    env_file = tmp_path / "fixture.env"
    env_file.write_text(
        "COMPOSE_PROJECT_NAME=businessaiagents-test\nPUBLIC_URL=https://research.example.test\n"
        "POSTGRES_PASSWORD=fixture\nOLLAMA_API_KEY=fixture\n"
        "LOCAL_OPENAI_BASE_URL=http://172.17.0.1:11437/v1\n"
        "LOCAL_OPENAI_API_KEY=fixture\nLOCAL_OPENAI_MODEL=fixture-model\n"
    )
    command = ["docker", "compose", "--env-file", str(env_file), "--profile", "local-ai",
               "-f", str(root / "docker-compose.yml")]
    if team:
        command += ["-f", str(root / "docker-compose.team.yml")]
    result = subprocess.run(command + ["config", "--format", "json"], env=os.environ.copy(),
                            capture_output=True, text=True, check=True)
    services = json.loads(result.stdout)["services"]
    for name in ("api", "worker"):
        configured = services[name]["environment"]
        assert configured["OLLAMA_API_KEY"] == "fixture"
        assert configured["LOCAL_OPENAI_BASE_URL"] == "http://172.17.0.1:11437/v1"
        assert configured["LOCAL_OPENAI_MODEL"] == "fixture-model"
        assert configured["LOCAL_OPENAI_API_KEY"] == "fixture"
        assert configured["LOCAL_AI_MAX_RESPONSE_BYTES"] == "2000000"
        if team:
            assert configured["AI_CLI_BRIDGE_URL"] == ""
    bridges = (("ollama-bridge", "ollama"), ("local-openai-bridge", "openai_compatible"))
    for name, protocol in bridges:
        service = services[name]
        assert service["environment"]["LOCAL_MODEL_BRIDGE_PROTOCOL"] == protocol
        assert service["network_mode"] == "host"
        assert not service.get("ports")
        assert service["read_only"]
        assert service["cap_drop"] == ["ALL"]
        if team:
            assert service["image"] == "businessaiagents-team-api:latest"
            assert not service.get("volumes")


def test_fresh_team_example_connects_api_and_worker_to_private_local_bridges(tmp_path):
    if not shutil.which("docker"):
        pytest.skip("Docker Compose is not installed")
    if subprocess.run(["docker", "compose", "version"], capture_output=True).returncode:
        pytest.skip("Docker Compose is not installed")
    root = Path(__file__).resolve().parents[3]
    template = (root / ".env.team.example").read_text()
    env_file = tmp_path / "team.env"
    env_file.write_text(
        template.replace("POSTGRES_PASSWORD=\n", "POSTGRES_PASSWORD=fixture\n")
        .replace("COMPOSE_PROFILES=https\n", "COMPOSE_PROFILES=https,local-ai\n")
    )
    # An operator's shell/.env must not fill gaps in this fresh-example proof.
    keys = {line.partition("=")[0] for line in template.splitlines() if "=" in line}
    environment = {key: value for key, value in os.environ.items() if key not in keys}
    result = subprocess.run(
        [
            "docker", "compose", "--env-file", str(env_file),
            "-f", str(root / "docker-compose.yml"),
            "-f", str(root / "docker-compose.team.yml"), "config", "--format", "json",
        ],
        env=environment, capture_output=True, text=True, check=True,
    )
    services = json.loads(result.stdout)["services"]
    for service in ("api", "worker"):
        configured = services[service]["environment"]
        assert configured["OLLAMA_BASE_URL"] == "http://172.17.0.1:11435"
        assert configured["LOCAL_OPENAI_BASE_URL"] == "http://172.17.0.1:11437/v1"
        assert configured["AUTH_MODE"] == "local"
        assert configured["AUTH_COOKIE_SECURE"] == "true"
    for service in ("ollama-bridge", "local-openai-bridge"):
        assert services[service]["network_mode"] == "host"
        assert not services[service].get("ports")
        assert not services[service].get("volumes")
