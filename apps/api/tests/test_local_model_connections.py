"""Local model contracts exercise the app with deterministic inference, no model download."""

import json

import pytest
from pydantic import BaseModel, SecretStr, ValidationError
from sqlalchemy import func, select

from app.core.config import Settings, settings
from app.models import ChatMessage, ChatSession, GraphChangeSet
from app.schemas.auth import UserCreate
from app.services import ai
from app.services.auth import create_user
from app.services.providers import local_models

BASE = "/api/v1/chat/connections/local/"


@pytest.fixture
def local_server(monkeypatch):
    state = {"models": ["fixture-a", "fixture-b"], "calls": [], "tools": []}
    monkeypatch.setattr(settings, "ollama_model", "fixture-a")
    monkeypatch.setattr(settings, "local_openai_model", "fixture-a")
    monkeypatch.setattr(settings, "local_openai_base_url", "http://127.0.0.1:1234/v1")
    monkeypatch.setattr(settings, "local_openai_api_key", SecretStr("synthetic-server-secret"))

    def request(provider, method, path, *, payload=None, timeout=None):
        state["calls"].append((provider, method, path, payload, timeout))
        if method == "GET":
            return (
                {"models": [{"name": name} for name in state["models"]]}
                if provider == "ollama"
                else {"data": [{"id": name} for name in state["models"]]}
            )
        output = json.dumps({"reply": "Local fixture answer.", "tool_calls": state["tools"]})
        return (
            {"message": {"content": output}, "done": True, "prompt_eval_count": 7, "eval_count": 4}
            if provider == "ollama"
            else {"choices": [{"message": {"content": output}, "finish_reason": "stop"}]}
        )

    monkeypatch.setattr(local_models, "_request", request)
    return state


@pytest.mark.parametrize("provider", ["ollama", "local_openai"])
def test_catalogue_and_probe_are_keyless_no_store_and_do_not_create_records(
    client, db, local_server, provider, caplog
):
    result = client.post(BASE + "models", json={"provider": provider})
    assert result.status_code == 200
    assert result.json() == {"provider": provider, "models": ["fixture-a", "fixture-b"]}
    assert result.headers["cache-control"] == "no-store"
    checked = client.post(BASE + "verify", json={"provider": provider, "model_name": "fixture-b"})
    assert checked.status_code == 200
    assert checked.json() == {"provider": provider, "model_name": "fixture-b", "verified": True}
    assert checked.headers["cache-control"] == "no-store"
    inference = [call for call in local_server["calls"] if call[1] == "POST"]
    assert len(inference) == 1
    payload = inference[0][3]
    assert payload["model"] == "fixture-b"
    assert payload.get("max_tokens", payload.get("options", {}).get("num_predict")) == 128
    assert inference[0][4] == 20
    assert db.scalar(select(func.count()).select_from(ChatSession)) == 0
    assert db.scalar(select(func.count()).select_from(ChatMessage)) == 0
    assert "synthetic-server-secret" not in result.text + checked.text + caplog.text


@pytest.mark.parametrize(
    "extra", [{"url": "http://127.0.0.1:1"}, {"personal_api_key": "secret-marker"}]
)
def test_local_connection_cannot_select_an_endpoint_or_send_a_personal_key(
    client, local_server, extra
):
    response = client.post(BASE + "models", json={"provider": "ollama", **extra})
    assert response.status_code == 422
    assert "secret-marker" not in response.text
    assert local_server["calls"] == []


def test_probe_and_create_reject_missing_model_before_inference(client, local_server):
    checked = client.post(BASE + "verify", json={"provider": "ollama", "model_name": "missing"})
    created = client.post(
        "/api/v1/chat/sessions", json={"provider": "ollama", "model_name": "missing"}
    )
    assert checked.status_code == created.status_code == 422
    assert checked.json()["error"]["code"] == "CHAT_MODEL_UNAVAILABLE"
    assert all(call[1] == "GET" for call in local_server["calls"])


@pytest.mark.parametrize("provider", ["ollama", "local_openai"])
def test_local_session_pins_model_after_operator_changes_default(
    client, monkeypatch, local_server, provider
):
    created = client.post(
        "/api/v1/chat/sessions", json={"provider": provider, "model_name": "fixture-b"}
    )
    assert created.status_code == 201
    session = created.json()
    assert session["credential_source"] == "system"
    assert session["model_name"] == "fixture-b"
    monkeypatch.setattr(
        settings, "ollama_model" if provider == "ollama" else "local_openai_model", "fixture-a"
    )
    turn = client.post(
        f"/api/v1/chat/sessions/{session['id']}/messages", json={"content": "Say hello."}
    )
    assert turn.status_code == 200
    assert turn.json()["assistant_message"]["error_code"] is None
    assert turn.json()["assistant_message"]["content"] == "Local fixture answer."
    assert [call[3]["model"] for call in local_server["calls"] if call[1] == "POST"] == [
        "fixture-b"
    ]


@pytest.mark.parametrize(
    "tool_call",
    [
        {"name": "search_nodes", "arguments_json": '{"query":123,"unknown":true}'},
        {"name": "search_graph", "arguments_json": "[1,2]"},
    ],
    ids=["unknown-tool", "non-object-arguments"],
)
def test_invalid_local_tool_calls_never_create_graph_changes(client, db, local_server, tool_call):
    session = client.post(
        "/api/v1/chat/sessions", json={"provider": "ollama", "model_name": "fixture-a"}
    ).json()
    local_server["tools"] = [tool_call]
    turn = client.post(
        f"/api/v1/chat/sessions/{session['id']}/messages", json={"content": "Find agents."}
    )
    assert turn.status_code == 502
    assert turn.json()["error"]["code"] == "CHAT_TOOL_VALIDATION_FAILED"
    assert db.scalar(select(func.count()).select_from(GraphChangeSet)) == 0
    failure = db.scalar(select(ChatMessage).where(ChatMessage.role == "assistant"))
    assert failure is not None and failure.error_code == "CHAT_TOOL_VALIDATION_FAILED"


@pytest.mark.parametrize("role", [None, "viewer", "researcher"])
def test_local_model_actions_enforce_login_roles_and_csrf(
    client, db, monkeypatch, local_server, role
):
    monkeypatch.setattr(settings, "auth_mode", "local")
    monkeypatch.setattr(settings, "auth_cookie_secure", False)
    headers = {}
    if role:
        create_user(
            db,
            UserCreate(
                name="Fixture",
                email="local@fixture.invalid",
                password="synthetic-password-123",
                role=role,
            ),
            actor="test",
        )
        client.post(
            "/api/v1/auth/login",
            json={"email": "local@fixture.invalid", "password": "synthetic-password-123"},
        )
        headers = {"X-CSRF-Token": client.cookies.get(settings.auth_csrf_cookie_name)}
    response = client.post(BASE + "models", json={"provider": "ollama"}, headers=headers)
    assert response.status_code == (401 if role is None else 403 if role == "viewer" else 200)
    if role == "researcher":
        assert (
            client.post(
                BASE + "verify", json={"provider": "ollama", "model_name": "fixture-a"}
            ).status_code
            == 403
        )
    else:
        assert local_server["calls"] == []


def test_local_model_inference_is_rate_limited(client, monkeypatch, local_server):
    monkeypatch.setattr(settings, "rate_limit_chat_per_window", 1)
    assert client.post(BASE + "models", json={"provider": "ollama"}).status_code == 200
    limited = client.post(BASE + "verify", json={"provider": "ollama", "model_name": "fixture-a"})
    assert limited.status_code == 429
    assert all(call[1] == "GET" for call in local_server["calls"])


@pytest.mark.parametrize(
    "endpoint",
    [
        "file:///tmp/model",
        "http://user:marker@localhost:1234",
        "http://localhost:1234?key=marker",
        "http://localhost:1234/#bad",
    ],
)
def test_local_endpoint_configuration_rejects_ambiguous_urls(tmp_path, endpoint):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, secret_files_dir=str(tmp_path), local_openai_base_url=endpoint)


def test_local_server_keys_use_existing_secret_file_boundary(tmp_path):
    (tmp_path / "local_openai_api_key").write_text("synthetic-file-secret\n")
    config = Settings(_env_file=None, secret_files_dir=str(tmp_path))
    assert config.local_openai_api_key.get_secret_value() == "synthetic-file-secret"
    assert "synthetic-file-secret" not in repr(config)


def test_structured_local_provider_preserves_pydantic_and_usage_contract(monkeypatch):
    class Answer(BaseModel):
        label: str

    captured = []

    def complete(provider, prompt, schema, max_output_tokens):
        captured.append((provider, prompt, schema, max_output_tokens))
        return {"label": "local"}, {"input_tokens": 7, "output_tokens": 3, "total_tokens": 10}

    monkeypatch.setattr(local_models, "complete_local_json", complete)
    for provider in (ai.OllamaProvider(), ai.LocalOpenAIProvider()):
        assert provider.complete_json("Return a label.", Answer).label == "local"
    assert [call[0] for call in captured] == ["ollama", "local_openai"]
    assert all(call[2] is Answer and call[3] == settings.ai_max_output_tokens for call in captured)
