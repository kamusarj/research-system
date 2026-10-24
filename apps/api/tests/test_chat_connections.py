"""No external requests: synthetic credentials and deterministic upstream fixtures."""

import json
from contextlib import contextmanager

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import func, select

from app.core.config import settings
from app.core.runtime_controls import rate_limiter
from app.models import ChatMessage, ChatSession
from app.schemas.auth import UserCreate
from app.schemas.chat import ChatModelsRequest, ChatVerifyRequest
from app.services.auth import create_user

KEY = "synthetic-connection-secret"
MODEL = "test-model-selected"
BASE = "/api/v1/chat/connections/"


def request(provider="openai", **extra):
    return {"provider": provider, "personal_api_key": KEY, **extra}


@pytest.fixture(autouse=True)
def upstream(monkeypatch):
    state = {"status": 200, "calls": [], "models": {"data": [{"id": MODEL}]}}

    def response(method, url, kwargs):
        state["calls"].append((method, url, kwargs))
        if "exception" in state:
            raise state["exception"]
        if method == "GET":
            payload = state["models"]
        elif "openai.com" in url:
            payload = {"output": [], "status": "incomplete"}
        else:
            payload = {"choices": [{"message": {"content": "OK"}}]}
        payload = state.get("payload", payload)
        return httpx.Response(state["status"], json=payload, request=httpx.Request(method, url))

    @contextmanager
    def stream(method, url, **kwargs):
        yield response(method, url, kwargs)

    monkeypatch.setattr(httpx, "stream", stream)
    monkeypatch.setattr(httpx, "post", lambda url, **kwargs: response("POST", url, kwargs))
    return state


@pytest.mark.parametrize("provider", ["openai", "deepseek"])
def test_discovery_and_probe_are_request_scoped_bounded_and_do_not_persist(
    client, db, monkeypatch, caplog, upstream, provider
):
    monkeypatch.setattr(settings, f"{provider}_api_key", SecretStr("synthetic-system-secret"))
    upstream["models"] = {
        "data": [
            {"id": MODEL},
            {"id": "z-model"},
            {"id": MODEL},
            {"id": "a-model"},
            {"id": "<script>bad</script>"},
            {"id": KEY},
            {"id": 123},
            None,
        ]
    }
    result = client.post(BASE + "models", json=request(provider))
    assert result.status_code == 200
    assert result.json() == {"provider": provider, "models": ["a-model", MODEL, "z-model"]}
    assert result.headers["cache-control"] == "no-store"
    assert [call[0] for call in upstream["calls"]] == ["GET"]
    discovery = upstream["calls"][0]
    assert discovery[1] == (
        "https://api.openai.com/v1/models"
        if provider == "openai"
        else "https://api.deepseek.com/models"
    )
    assert discovery[2]["follow_redirects"] is False
    assert discovery[2]["timeout"] == 20

    checked = client.post(BASE + "verify", json=request(provider, model_name=MODEL))
    assert checked.status_code == 200
    assert checked.json() == {"provider": provider, "model_name": MODEL, "verified": True}
    assert checked.headers["cache-control"] == "no-store"
    method, url, kwargs = upstream["calls"][-1]
    assert method == "POST"
    assert url == (
        "https://api.openai.com/v1/responses"
        if provider == "openai"
        else "https://api.deepseek.com/chat/completions"
    )
    assert kwargs["timeout"] == 20
    payload = kwargs["json"]
    assert payload["model"] == MODEL
    assert payload.get("max_output_tokens", payload.get("max_tokens")) == 16
    assert len(payload["tools"]) == 1
    assert payload["tool_choice"] == "auto"
    assert "Reply OK." in json.dumps(payload)
    if provider == "openai":
        assert payload["store"] is False
        assert payload["parallel_tool_calls"] is True
    else:
        assert payload["thinking"] == {"type": "disabled"}
    assert len(upstream["calls"]) == 2
    assert all(call[2]["headers"]["Authorization"] == f"Bearer {KEY}" for call in upstream["calls"])
    assert KEY not in result.text + checked.text + caplog.text
    assert db.scalar(select(func.count()).select_from(ChatSession)) == 0
    assert db.scalar(select(func.count()).select_from(ChatMessage)) == 0


@pytest.mark.parametrize(
    "provider,status,error,expected,http_status",
    [
        ("openai", 401, {}, "CHAT_API_KEY_INVALID", 422),
        ("deepseek", 401, {}, "CHAT_API_KEY_INVALID", 422),
        ("deepseek", 402, {}, "CHAT_CREDIT_EXHAUSTED", 402),
        (
            "openai",
            429,
            {"code": "credit_balance_exhausted", "type": "insufficient_quota"},
            "CHAT_CREDIT_EXHAUSTED",
            402,
        ),
        (
            "openai",
            429,
            {"code": "project_spend_limit_exceeded", "type": "insufficient_quota"},
            "CHAT_SPEND_LIMIT_REACHED",
            402,
        ),
        (
            "openai",
            429,
            {"code": "organization_spend_limit_exceeded"},
            "CHAT_SPEND_LIMIT_REACHED",
            402,
        ),
        (
            "openai",
            429,
            {"code": "organization_usage_limit_exceeded"},
            "CHAT_USAGE_LIMIT_REACHED",
            402,
        ),
        ("openai", 429, {"code": "insufficient_quota"}, "CHAT_QUOTA_EXCEEDED", 402),
        ("openai", 429, {"type": "insufficient_quota"}, "CHAT_QUOTA_EXCEEDED", 402),
        ("openai", 429, {"code": "rate_limit_exceeded"}, "CHAT_PROVIDER_RATE_LIMITED", 429),
        ("deepseek", 429, {}, "CHAT_PROVIDER_RATE_LIMITED", 429),
        ("openai", 403, {}, "CHAT_API_ACCESS_DENIED", 422),
        ("openai", 404, {"code": "model_not_found"}, "CHAT_MODEL_UNAVAILABLE", 422),
        ("deepseek", 400, {"code": "invalid_model"}, "CHAT_MODEL_UNAVAILABLE", 422),
        ("deepseek", 400, {"message": "Model does not exist"}, "CHAT_MODEL_UNAVAILABLE", 422),
        ("openai", 400, {"param": "tools"}, "CHAT_MODEL_INCOMPATIBLE", 422),
        ("openai", 400, {"code": "unsupported_model"}, "CHAT_MODEL_INCOMPATIBLE", 422),
        (
            "deepseek",
            422,
            {"message": "Model does not support tools"},
            "CHAT_MODEL_INCOMPATIBLE",
            422,
        ),
        ("deepseek", 422, {}, "CHAT_PROVIDER_REQUEST_REJECTED", 422),
        ("openai", 500, {}, "CHAT_PROVIDER_UNAVAILABLE", 503),
        ("deepseek", 503, {}, "CHAT_PROVIDER_UNAVAILABLE", 503),
    ],
)
def test_distinct_safe_errors_and_no_retry(
    client, caplog, upstream, provider, status, error, expected, http_status
):
    upstream.update(
        status=status, payload={"error": {**error, "message": f"{error.get('message', '')} {KEY}"}}
    )
    response = client.post(BASE + "verify", json=request(provider, model_name=MODEL))
    assert response.status_code == http_status
    assert response.json()["error"]["code"] == expected
    assert KEY not in response.text + caplog.text
    assert response.headers["cache-control"] == "no-store"
    assert len(upstream["calls"]) == 1


@pytest.mark.parametrize("endpoint", ["models", "verify"])
def test_request_validation_never_echoes_key(client, upstream, endpoint):
    for body in (
        {"provider": "openai"},
        request(personal_api_key=None),
        request(personal_api_key=KEY + "\n"),
        request("http://localhost"),
        request(personal_api_key="short"),
        request(model_name="../not a model"),
    ):
        # Model-name validity belongs only to the verification request.
        if endpoint == "models" and "model_name" in body:
            continue
        response = client.post(BASE + endpoint, json=body)
        assert response.status_code == 422
        assert KEY not in response.text
    assert upstream["calls"] == []


@pytest.mark.parametrize("schema", [ChatModelsRequest, ChatVerifyRequest])
def test_schema_excludes_secret(schema):
    parsed = schema(**request(model_name=MODEL))
    assert KEY not in repr(parsed) + parsed.model_dump_json()
    assert "personal_api_key" not in parsed.model_dump()


@pytest.mark.parametrize("payload", [None, [], {}, {"data": None}, {"data": "wrong"}])
def test_invalid_catalogue_not_reported_as_success(client, upstream, payload):
    upstream["models"] = payload
    response = client.post(BASE + "models", json=request())
    assert response.status_code == 502


def test_empty_and_oversize_catalogue(client, upstream):
    upstream["models"] = {"data": []}
    assert client.post(BASE + "models", json=request()).json()["models"] == []
    upstream["models"] = {"data": [{"id": f"m-{i}"} for i in range(1001)]}
    assert client.post(BASE + "models", json=request()).status_code == 502
    upstream["models"] = {"data": [], "padding": "x" * 2_000_001}
    assert client.post(BASE + "models", json=request()).status_code == 502


@pytest.mark.parametrize(
    "status,expected",
    [
        (401, "CHAT_API_KEY_INVALID"),
        (403, "CHAT_API_ACCESS_DENIED"),
        (404, "CHAT_PROVIDER_FAILED"),
        (429, "CHAT_PROVIDER_RATE_LIMITED"),
        (302, "CHAT_PROVIDER_FAILED"),
    ],
)
def test_discovery_http_errors(client, upstream, status, expected):
    upstream.update(status=status, payload={"error": {"message": KEY}})
    response = client.post(BASE + "models", json=request())
    assert response.json()["error"]["code"] == expected
    assert KEY not in response.text
    assert len(upstream["calls"]) == 1


@pytest.mark.parametrize("endpoint", ["models", "verify"])
@pytest.mark.parametrize(
    "exception,expected",
    [
        (httpx.ReadTimeout("redacted"), "CHAT_PROVIDER_TIMEOUT"),
        (httpx.ConnectError("redacted"), "CHAT_PROVIDER_UNAVAILABLE"),
    ],
)
def test_network_errors(client, upstream, endpoint, exception, expected):
    upstream["exception"] = exception
    response = client.post(BASE + endpoint, json=request(model_name=MODEL))
    assert response.json()["error"]["code"] == expected


@pytest.mark.parametrize(
    "provider,payload",
    [
        ("openai", {}),
        ("openai", {"status": "failed", "output": [], "error": {"code": "insufficient_quota"}}),
        ("deepseek", {"choices": []}),
    ],
)
def test_invalid_or_failed_200_probe_is_not_success(client, upstream, provider, payload):
    upstream["payload"] = payload
    response = client.post(BASE + "verify", json=request(provider, model_name=MODEL))
    assert response.status_code >= 400
    assert "verified" not in response.json()


def test_auth_roles_csrf_and_connection_rate_limit(client, db, monkeypatch, upstream):
    monkeypatch.setattr(settings, "auth_mode", "local")
    monkeypatch.setattr(settings, "auth_cookie_secure", False)
    for endpoint in ("models", "verify"):
        assert client.post(BASE + endpoint, json=request(model_name=MODEL)).status_code == 401
    for role in ("viewer", "researcher", "owner"):
        create_user(
            db,
            UserCreate(
                name=role, email=f"{role}@example.com", password="synthetic-password-123", role=role
            ),
            actor="test",
        )
        client.cookies.clear()
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": f"{role}@example.com", "password": "synthetic-password-123"},
            ).status_code
            == 200
        )
        headers = {"X-CSRF-Token": client.cookies[settings.auth_csrf_cookie_name]}
        for endpoint in ("models", "verify"):
            assert client.post(BASE + endpoint, json=request(model_name=MODEL)).status_code == 403
            response = client.post(BASE + endpoint, headers=headers, json=request(model_name=MODEL))
            assert response.status_code == (403 if role == "viewer" else 200)
    assert len(upstream["calls"]) == 4
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_chat_per_window", 1)
    rate_limiter.clear()
    try:
        assert client.post(BASE + "models", headers=headers, json=request()).status_code == 200
        response = client.post(BASE + "verify", headers=headers, json=request(model_name=MODEL))
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "RATE_LIMITED"
        assert len(upstream["calls"]) == 5
    finally:
        rate_limiter.clear()
