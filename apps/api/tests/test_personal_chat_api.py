"""Synthetic credentials only; all outbound provider requests are intercepted."""

import json

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import func, select

from app.core.config import settings
from app.models import ChatMessage
from app.schemas.auth import UserCreate
from app.schemas.chat import ChatSessionCreate
from app.services.auth import create_user
from app.services.chatgpt_import import ChatGPTSharedSnapshot, ImportedChatMessage

KEY_A = "synthetic-personal-key-alpha"
KEY_B = "synthetic-personal-key-bravo"


def personal_request(provider="openai", key=KEY_A):
    return {
        "provider": provider,
        "credential_source": "personal",
        "model_name": "personal-test-model",
        "personal_api_key": key,
    }


def intercept_provider(monkeypatch, *, status=200):
    requests = []

    def post(url, **kwargs):
        requests.append((url, kwargs))
        payload = (
            {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Personal API answer."}],
                    }
                ]
            }
            if "openai.com" in url
            else {"choices": [{"message": {"content": "Personal API answer."}}]}
        )
        if status != 200:
            payload = {"error": {"message": f"upstream echoes {KEY_A}"}}
        return httpx.Response(status, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", post)
    return requests


@pytest.mark.parametrize("provider", ["openai", "deepseek"])
def test_personal_key_is_request_scoped_and_never_persisted(
    client, db, monkeypatch, caplog, provider
):
    system_key = SecretStr("synthetic-system-key")
    monkeypatch.setattr(settings, f"{provider}_api_key", system_key)
    calls = intercept_provider(monkeypatch)
    response = client.post("/api/v1/chat/sessions", json=personal_request(provider))
    assert response.status_code == 201
    session = response.json()
    assert session["credential_source"] == "personal"
    assert session["model_name"] == "personal-test-model"
    assert calls == []  # Creating a connection never spends tokens.
    for key in (KEY_A, KEY_B):
        turn = client.post(
            f"/api/v1/chat/sessions/{session['id']}/messages",
            json={
                "content": "Please explain the current scope.",
                "personal_api_key": key,
                "model_name": "cannot-override-session-model",
            },
        )
        assert turn.status_code == 200
        assert turn.json()["assistant_message"]["content"] == "Personal API answer."
        assert key not in turn.text
    assert [call[1]["headers"]["Authorization"] for call in calls] == [
        f"Bearer {KEY_A}",
        f"Bearer {KEY_B}",
    ]
    for url, kwargs in calls:
        assert url in {
            "https://api.openai.com/v1/responses",
            "https://api.deepseek.com/chat/completions",
        }
        assert kwargs["json"]["model"] == "personal-test-model"
        assert KEY_A not in json.dumps(kwargs["json"])
        assert KEY_B not in json.dumps(kwargs["json"])
    assert getattr(settings, f"{provider}_api_key") is system_key
    dump = "\n".join(db.connection().connection.driver_connection.iterdump())
    for key in (KEY_A, KEY_B):
        assert key not in dump
        assert key not in caplog.text
        assert key not in client.get("/api/v1/chat/sessions").text


def test_missing_personal_key_never_falls_back_or_writes_a_message(client, db, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", SecretStr("synthetic-system-key"))
    calls = intercept_provider(monkeypatch)
    session = client.post("/api/v1/chat/sessions", json=personal_request()).json()
    response = client.post(
        f"/api/v1/chat/sessions/{session['id']}/messages", json={"content": "Hi"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CHAT_PERSONAL_KEY_REQUIRED"
    assert db.scalar(select(func.count()).select_from(ChatMessage)) == 0
    assert calls == []


@pytest.mark.parametrize("key", ["short", "contains\nnewline", "too-long-" * 600])
def test_invalid_keys_are_not_echoed(client, key):
    response = client.post("/api/v1/chat/sessions", json=personal_request(key=key))
    assert response.status_code == 422
    assert key not in response.text
    assert "input" not in response.text


def test_secret_is_excluded_from_request_repr_and_serialization():
    request = ChatSessionCreate(**personal_request())
    assert KEY_A not in repr(request)
    assert KEY_A not in request.model_dump_json()
    assert "personal_api_key" not in request.model_dump()


def test_personal_and_system_requests_cannot_be_mixed(client, db, monkeypatch):
    bad = client.post(
        "/api/v1/chat/sessions", json={**personal_request(), "credential_source": "system"}
    )
    assert bad.status_code == 422
    session = client.post("/api/v1/chat/sessions", json={"provider": "openai"}).json()
    calls = intercept_provider(monkeypatch)
    turn = client.post(
        f"/api/v1/chat/sessions/{session['id']}/messages",
        json={"content": "Hi", "personal_api_key": KEY_A},
    )
    assert turn.status_code == 422
    assert turn.json()["error"]["code"] == "CHAT_CREDENTIAL_MISMATCH"
    assert db.scalar(select(func.count()).select_from(ChatMessage)) == 0
    assert calls == []


def test_provider_auth_failure_does_not_expose_secret_or_use_fallback(client, monkeypatch, caplog):
    calls = intercept_provider(monkeypatch, status=401)
    session = client.post("/api/v1/chat/sessions", json=personal_request()).json()
    response = client.post(
        f"/api/v1/chat/sessions/{session['id']}/messages",
        json={"content": "Hi", "personal_api_key": KEY_A},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CHAT_API_KEY_INVALID"
    history = client.get(f"/api/v1/chat/sessions/{session['id']}/messages")
    assert history.json()[-1]["error_code"] == "CHAT_API_KEY_INVALID"
    assert KEY_A not in history.text
    assert KEY_A not in response.text + caplog.text
    assert len(calls) == 1


def test_personal_chatgpt_import_keeps_only_connection_metadata(client, monkeypatch):
    snapshot = ChatGPTSharedSnapshot(
        canonical_url="https://chatgpt.com/share/12345678-1234-1234-1234-123456789abc",
        title="Imported personal chat",
        snapshot_hash="a" * 64,
        total_characters=17,
        messages=(ImportedChatMessage(role="user", content="Original question"),),
    )
    monkeypatch.setattr(
        "app.services.graph_chat.import_chatgpt_shared_snapshot", lambda *args: snapshot
    )
    response = client.post(
        "/api/v1/chat/imports/chatgpt",
        json={**personal_request("deepseek"), "url": snapshot.canonical_url},
    )
    assert response.status_code == 201
    assert response.json()["credential_source"] == "personal"
    assert response.json()["source_type"] == "chatgpt_shared"
    assert KEY_A not in response.text


def test_auth_roles_csrf_and_different_users_keep_keys_separate(client, db, monkeypatch):
    monkeypatch.setattr(settings, "auth_mode", "local")
    monkeypatch.setattr(settings, "auth_cookie_secure", False)
    calls = intercept_provider(monkeypatch)
    assert client.post("/api/v1/chat/sessions", json=personal_request()).status_code == 401
    for role in ("viewer", "researcher", "owner"):
        create_user(
            db,
            UserCreate(
                name=role, email=f"{role}@example.com", password="synthetic-password-123", role=role
            ),
            actor="test",
        )
    session_id = None
    for role, key in (("viewer", KEY_A), ("researcher", KEY_A), ("owner", KEY_B)):
        client.cookies.clear()
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": f"{role}@example.com", "password": "synthetic-password-123"},
            ).status_code
            == 200
        )
        assert (
            client.post("/api/v1/chat/sessions", json=personal_request(key=key)).status_code == 403
        )
        headers = {"X-CSRF-Token": client.cookies[settings.auth_csrf_cookie_name]}
        response = client.post(
            "/api/v1/chat/sessions", headers=headers, json=personal_request(key=key)
        )
        if role == "viewer":
            assert response.status_code == 403
            continue
        assert response.status_code == 201
        session_id = session_id or response.json()["id"]
        # A second user must supply their own key even for an existing shared personal chat.
        assert (
            client.post(
                f"/api/v1/chat/sessions/{session_id}/messages",
                headers=headers,
                json={"content": "Hi"},
            ).status_code
            == 422
        )
        assert (
            client.post(
                f"/api/v1/chat/sessions/{session_id}/messages",
                headers=headers,
                json={"content": "Hi", "personal_api_key": key},
            ).status_code
            == 200
        )
    assert [call[1]["headers"]["Authorization"] for call in calls] == [
        f"Bearer {KEY_A}",
        f"Bearer {KEY_B}",
    ]
