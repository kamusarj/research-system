"""Gói ChatGPT riêng của người dùng: OAuth (Sign in with ChatGPT), token mã hóa, Responses API.

OpenAI được giả lập bằng `httpx.MockTransport` theo đúng hợp đồng trong tài liệu SIWC, nên test
không gọi mạng và không cần tài khoản thật.
"""

import base64
import hashlib
import json
import logging
import time
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import httpx
import jwt
import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import BaseModel, SecretStr
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings, settings
from app.core.observability import OAuthCallbackLogFilter
from app.models import AIPlanConnection, AuditEvent, LinkSubmission, ResearchRun
from app.services import chatgpt_plan
from app.services.ai import PROVIDERS, ChatGPTPlanProvider
from app.services.ai import provider as real_provider
from app.services.credentials_vault import decrypt_json
from app.services.providers.openai_graph_chat import graph_chat_provider

ISSUER = "https://auth.openai.com"
ISSUED = "oaiapp_test123"
SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PLAN_SCOPES = "chatgpt.tokens.use.direct email offline_access openid profile resource.invoke"


class Answer(BaseModel):
    answer: str


def sse(*events: dict) -> bytes:
    return "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()


def completed(output: dict, usage: dict | None = None) -> bytes:
    text = json.dumps(output)
    return sse(
        {"type": "response.created"},
        {"type": "response.output_text.delta", "delta": text[:4]},
        {"type": "response.output_text.delta", "delta": text[4:]},
        {
            "type": "response.completed",
            "response": {
                "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
                "usage": usage or {"input_tokens": 12, "output_tokens": 5},
            },
        },
    )


class FakeOpenAI:
    """auth.openai.com + api.openai.com đủ cho luồng đăng nhập, làm mới, thu hồi và suy luận."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.nonce = ""
        self.challenge = ""
        self.subject = "chatgpt-user-1"
        self.scope = PLAN_SCOPES
        self.refreshes = 0
        self.refresh_status = 200
        self.refresh_error = ""
        self.responses: list[tuple[int, object]] = []
        self.revoked: list[dict[str, list[str]]] = []

    def id_token(self, audience: str) -> str:
        now = int(time.time())
        claims = {
            "iss": ISSUER,
            "aud": audience,
            "sub": self.subject,
            "email": "linh@example.com",
            "iat": now,
            "exp": now + 600,
            "nonce": self.nonce,
        }
        return jwt.encode(claims, SIGNING_KEY, algorithm="RS256")

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path == "/.well-known/openid-configuration":
            return httpx.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "authorization_endpoint": f"{ISSUER}/oauth/authorize",
                    "token_endpoint": f"{ISSUER}/oauth/token",
                    "jwks_uri": f"{ISSUER}/.well-known/jwks.json",
                    "revocation_endpoint": f"{ISSUER}/oauth/revoke",
                },
            )
        if path.endswith("/oauth/token"):
            form = parse_qs(request.content.decode())
            assert form["resource"] == ["https://api.openai.com/v1"]
            if form["grant_type"] == ["authorization_code"]:
                verifier = form["code_verifier"][0].encode()
                digest = base64.urlsafe_b64encode(hashlib.sha256(verifier).digest())
                assert digest.rstrip(b"=").decode() == self.challenge, "PKCE mismatch"
                return httpx.Response(
                    200,
                    json={
                        "access_token": "at-1",
                        "refresh_token": "rt-1",
                        "id_token": self.id_token(form["client_id"][0]),
                        "token_type": "Bearer",
                        "expires_in": 3600,
                        "scope": self.scope,
                    },
                )
            self.refreshes += 1
            assert form["client_id"] == [ISSUED]
            if self.refresh_status != 200:
                return httpx.Response(self.refresh_status, json={"error": self.refresh_error})
            serial = self.refreshes + 1
            return httpx.Response(
                200,
                json={
                    "access_token": f"at-{serial}",
                    "refresh_token": f"rt-{serial}",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )
        if path.endswith("/oauth/revoke"):
            self.revoked.append(parse_qs(request.content.decode()))
            return httpx.Response(200)
        if str(request.url) == "https://api.openai.com/v1/models":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "slug": "gpt-6.1-sol",
                            "display_name": "GPT-6.1 Sol",
                            "visibility": "list",
                        },
                        {"slug": "internal-only", "display_name": "x", "visibility": "hide"},
                    ]
                },
            )
        if str(request.url) == "https://api.openai.com/v1/responses":
            status, payload = (
                self.responses.pop(0) if self.responses else (200, completed({"answer": "ok"}))
            )
            if status != 200:
                return httpx.Response(status, json=payload)
            return httpx.Response(
                200,
                content=payload,
                headers={"content-type": "text/event-stream", "x-request-id": "req_123"},
            )
        return httpx.Response(404)

    def inference_requests(self) -> list[httpx.Request]:
        return [r for r in self.requests if str(r.url) == "https://api.openai.com/v1/responses"]


@pytest.fixture
def fake(db, monkeypatch) -> FakeOpenAI:
    openai = FakeOpenAI()
    monkeypatch.setattr(settings, "chatgpt_plan_enabled", True)
    monkeypatch.setattr(settings, "chatgpt_plan_client_id", "")
    monkeypatch.setattr(
        settings, "credentials_encryption_key", SecretStr(Fernet.generate_key().decode())
    )
    monkeypatch.setattr(settings, "api_cors_origins", "http://localhost:13000")
    monkeypatch.setattr(chatgpt_plan, "transport", httpx.MockTransport(openai.handler))
    monkeypatch.setattr(chatgpt_plan, "session_factory", sessionmaker(bind=db.get_bind()))
    monkeypatch.setattr(chatgpt_plan, "_signing_key", lambda _token: SIGNING_KEY.public_key())
    monkeypatch.setattr(chatgpt_plan, "_discovery_cache", None)
    return openai


def start(client, fake: FakeOpenAI) -> dict[str, str]:
    response = client.post("/api/v1/ai-connections/chatgpt/start")
    assert response.status_code == 200, response.text
    params = {
        k: v[0] for k, v in parse_qs(urlsplit(response.json()["authorize_url"]).query).items()
    }
    fake.nonce = params["nonce"]
    fake.challenge = params["code_challenge"]
    return params


def connect(client, fake: FakeOpenAI) -> dict:
    params = start(client, fake)
    response = client.post(
        "/api/v1/ai-connections/chatgpt/complete",
        json={"state": params["state"], "code": "code-1", "client_id": ISSUED},
    )
    assert response.status_code == 200, response.text
    return response.json()


def stored(db) -> AIPlanConnection:
    db.expire_all()
    return db.scalar(select(AIPlanConnection))


def test_local_mode_authorize_request_follows_the_open_source_contract(client, fake):
    url = client.post("/api/v1/ai-connections/chatgpt/start").json()["authorize_url"]
    parts = urlsplit(url)
    params = {k: v[0] for k, v in parse_qs(parts.query).items()}

    assert f"{parts.scheme}://{parts.netloc}{parts.path}" == f"{ISSUER}/api/accounts/authorize"
    assert params["client_id"] == "dynamic_agent_client"
    assert params["agent_name_hint"] == "Business AI Agents"
    assert params["ext_agent_host_id"].startswith("urn:uuid:")
    assert params["redirect_uri"] == "http://127.0.0.1:18000/auth/callback"
    assert set(params["scope"].split()) == set(PLAN_SCOPES.split())
    assert params["resource"] == "https://api.openai.com/v1"
    assert params["code_challenge_method"] == "S256"
    assert "id_token_hint" not in params
    # Host ID ổn định giữa các lần bắt đầu và không chứa thông tin người dùng.
    again = client.post("/api/v1/ai-connections/chatgpt/start").json()["authorize_url"]
    assert parse_qs(urlsplit(again).query)["ext_agent_host_id"] == [params["ext_agent_host_id"]]
    assert "local" not in params["ext_agent_host_id"]


def test_connect_stores_only_encrypted_tokens_and_lists_visible_models(client, db, fake):
    status = connect(client, fake)

    assert status["status"] == "active"
    assert status["email"] == "linh@example.com"
    assert status["model"] == "gpt-6.1-sol"
    assert [m["slug"] for m in status["models"]] == ["gpt-6.1-sol"]
    assert "at-1" not in json.dumps(status) and "rt-1" not in json.dumps(status)

    connection = stored(db)
    assert connection.client_id == ISSUED
    assert "at-1" not in connection.encrypted_tokens and "rt-1" not in connection.encrypted_tokens
    tokens = decrypt_json(connection.encrypted_tokens)
    assert tokens["access_token"] == "at-1" and tokens["refresh_token"] == "rt-1"
    audit = db.scalar(select(AuditEvent).where(AuditEvent.action == "ai_plan.connected"))
    assert audit is not None
    assert "linh@example.com" not in json.dumps(audit.payload)
    assert "at-1" not in json.dumps(audit.payload)


def test_loopback_callback_forwards_to_the_signed_in_web_page(client, fake):
    response = client.get(
        "/auth/callback?code=abc&state=s1&client_id=oaiapp_x&evil=1",
        headers={"Host": "127.0.0.1:18000"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    target = urlsplit(response.headers["location"])
    assert f"{target.scheme}://{target.netloc}{target.path}" == (
        "http://localhost:13000/account/ai/callback"
    )
    assert parse_qs(target.query) == {"code": ["abc"], "state": ["s1"], "client_id": ["oaiapp_x"]}
    assert response.headers["cache-control"] == "no-store"


def test_loopback_callback_is_hidden_unless_local_plan_mode(client, fake, monkeypatch):
    monkeypatch.setattr(settings, "chatgpt_plan_client_id", "oaiapp_partner")
    assert client.get("/auth/callback?code=a&state=b", follow_redirects=False).status_code == 404
    monkeypatch.setattr(settings, "chatgpt_plan_client_id", "")
    monkeypatch.setattr(settings, "chatgpt_plan_enabled", False)
    assert client.get("/auth/callback?code=a&state=b", follow_redirects=False).status_code == 404


def test_state_is_single_use_and_bound_to_the_user_who_started(client, db, fake):
    params = start(client, fake)
    with pytest.raises(chatgpt_plan.ChatGPTPlanError) as stolen:
        # Kẻ tấn công lừa người khác hoàn tất: phiên không khớp người bắt đầu nên bị từ chối.
        chatgpt_plan.complete_authorization(
            db, "someone-else", state=params["state"], code="code-1", callback_client_id=ISSUED
        )
    assert stolen.value.code == "CHATGPT_PLAN_STATE_INVALID"

    params = start(client, fake)
    body = {"state": params["state"], "code": "code-1", "client_id": ISSUED}
    assert client.post("/api/v1/ai-connections/chatgpt/complete", json=body).status_code == 200
    replay = client.post("/api/v1/ai-connections/chatgpt/complete", json=body)
    assert replay.status_code == 400
    assert replay.json()["error"]["code"] == "CHATGPT_PLAN_STATE_INVALID"


def test_new_registration_requires_the_issued_client_id(client, fake):
    params = start(client, fake)
    response = client.post(
        "/api/v1/ai-connections/chatgpt/complete",
        json={"state": params["state"], "code": "code-1"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CHATGPT_PLAN_AUTH_FAILED"


def test_id_token_nonce_must_match_the_attempt(client, fake):
    params = start(client, fake)
    fake.nonce = "a-different-nonce"
    response = client.post(
        "/api/v1/ai-connections/chatgpt/complete",
        json={"state": params["state"], "code": "code-1", "client_id": ISSUED},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CHATGPT_PLAN_IDENTITY_INVALID"


def test_sign_in_without_plan_permission_never_reaches_inference(client, fake):
    fake.scope = "email offline_access openid profile"
    status = connect(client, fake)
    assert status["status"] == "plan_disabled"
    with pytest.raises(chatgpt_plan.ChatGPTPlanError) as error:
        ChatGPTPlanProvider("local-user").complete_json("prompt", Answer)
    assert error.value.code == "CHATGPT_PLAN_SCOPE_MISSING"
    assert fake.inference_requests() == []
    # Bật lại sau khi từ chối: hỏi lại sự đồng ý.
    assert start(client, fake)["prompt"] == "consent"


def test_structured_completion_streams_with_the_users_token(client, fake):
    connect(client, fake)
    result = real_provider("chatgpt_plan", user_id="local-user").complete_json(
        "Classify this", Answer
    )
    assert result.answer == "ok"

    [request] = fake.inference_requests()
    assert request.headers["authorization"] == "Bearer at-1"
    body = json.loads(request.content)
    assert body["store"] is False and body["stream"] is True
    assert body["model"] == "gpt-6.1-sol"
    assert body["input"] == [{"role": "user", "content": "Classify this"}]
    assert body["instructions"]
    assert body["text"]["format"]["type"] == "json_schema"
    for unsupported in ("temperature", "max_output_tokens", "metadata", "user", "top_p"):
        assert unsupported not in body


def test_access_token_is_refreshed_and_rotated_near_expiry(client, db, fake):
    connect(client, fake)
    connection = stored(db)
    connection.access_expires_at = chatgpt_plan.utcnow() + timedelta(minutes=1)
    db.commit()

    ChatGPTPlanProvider("local-user").complete_json("prompt", Answer)

    assert fake.refreshes == 1
    assert fake.inference_requests()[-1].headers["authorization"] == "Bearer at-2"
    tokens = decrypt_json(stored(db).encrypted_tokens)
    assert tokens["refresh_token"] == "rt-2"


def test_unusable_refresh_token_requires_signing_in_again(client, db, fake):
    connect(client, fake)
    connection = stored(db)
    connection.access_expires_at = chatgpt_plan.utcnow() - timedelta(minutes=1)
    db.commit()
    fake.refresh_status, fake.refresh_error = 400, "refresh_token_reused"

    with pytest.raises(chatgpt_plan.ChatGPTPlanError) as error:
        ChatGPTPlanProvider("local-user").complete_json("prompt", Answer)

    assert error.value.code == "CHATGPT_PLAN_REAUTH_REQUIRED"
    connection = stored(db)
    assert connection.status == "reauth_required"
    assert "refresh_token" not in decrypt_json(connection.encrypted_tokens)
    # Lần kết nối lại dùng đúng đăng ký cũ và gợi ý tài khoản, không đăng ký mới.
    params = start(client, fake)
    assert params["client_id"] == ISSUED
    assert "agent_name_hint" not in params
    assert params["login_hint"] == "linh@example.com"


def test_rejected_access_token_is_refreshed_once_then_retried(client, fake):
    connect(client, fake)
    fake.responses = [(401, {"detail": "token revoked"}), (200, completed({"answer": "again"}))]
    assert ChatGPTPlanProvider("local-user").complete_json("prompt", Answer).answer == "again"
    assert fake.refreshes == 1


def test_usage_limit_stops_without_switching_billing_path(client, db, fake):
    connect(client, fake)
    fake.responses = [
        (
            200,
            sse(
                {"type": "response.created"},
                {
                    "type": "response.failed",
                    "response": {"error": {"code": "subscription_sharing_usage_limit_exceeded"}},
                },
            ),
        )
    ]
    with pytest.raises(chatgpt_plan.ChatGPTPlanError) as error:
        ChatGPTPlanProvider("local-user").complete_json("prompt", Answer)
    assert error.value.code == "CHATGPT_PLAN_LIMIT_REACHED"
    assert error.value.status_code == 429 and not error.value.retryable
    assert stored(db).last_error_code == "CHATGPT_PLAN_LIMIT_REACHED"
    assert stored(db).status == "active"  # Không xóa đăng nhập vì hết hạn mức.


def test_temporary_admission_failure_is_retryable(client, fake):
    connect(client, fake)
    fake.responses = [(503, {"detail": "direct routing unavailable"})]
    with pytest.raises(chatgpt_plan.ChatGPTPlanError) as error:
        ChatGPTPlanProvider("local-user").complete_json("prompt", Answer)
    assert error.value.code == "CHATGPT_PLAN_UNAVAILABLE" and error.value.retryable


def test_disconnect_revokes_refresh_token_and_keeps_registration(client, db, fake):
    connect(client, fake)
    response = client.post("/api/v1/ai-connections/chatgpt/disconnect", json={})
    assert response.status_code == 200
    assert response.json()["remote_revoked"] is True
    assert response.json()["connection"]["status"] == "signed_out"
    assert fake.revoked == [
        {"token": ["rt-1"], "token_type_hint": ["refresh_token"], "client_id": [ISSUED]}
    ]
    connection = stored(db)
    assert connection.encrypted_tokens is None and connection.client_id == ISSUED
    params = start(client, fake)
    assert params["client_id"] == ISSUED and "id_token_hint" not in params

    forget = client.post("/api/v1/ai-connections/chatgpt/disconnect", json={"forget": True})
    assert forget.json()["connection"]["status"] == "not_connected"
    assert start(client, fake)["client_id"] == "dynamic_agent_client"


def test_model_choice_is_limited_to_the_account_catalog(client, fake):
    connect(client, fake)
    rejected = client.post(
        "/api/v1/ai-connections/chatgpt/preferences", json={"model": "internal-only"}
    )
    assert rejected.status_code == 422
    accepted = client.post(
        "/api/v1/ai-connections/chatgpt/preferences", json={"use_by_default": False}
    )
    assert accepted.json()["use_by_default"] is False


def test_new_research_defaults_to_the_users_connected_plan(client, db, fake, monkeypatch):
    from app.services.research_agent import runner

    monkeypatch.setattr(settings, "research_agent_enabled", True)
    connect(client, fake)
    run = runner.create_run(db, "Thị trường AI agent cho doanh nghiệp?", actor="local-user")
    assert run.provider_name == "chatgpt_plan"

    stored(db).use_by_default = False
    db.commit()
    other = runner.create_run(
        db, "Câu hỏi khác về AI agent?", actor="someone", enforce_limits=False
    )
    assert other.provider_name != "chatgpt_plan"


def test_worker_bills_the_research_run_creator(db, fake, monkeypatch):
    from app.services.research_agent import runner

    captured: dict[str, object] = {}

    def capture(name=None, *, user_id=None):
        captured.update(name=name, user_id=user_id)
        raise RuntimeError("stop after provider selection")

    monkeypatch.setattr(runner, "provider", capture)
    run = ResearchRun(
        question="q", provider_name="chatgpt_plan", created_by="alice", status="running"
    )
    db.add(run)
    db.commit()
    with pytest.raises(RuntimeError):
        runner.advance_research_run(db, run, providers=[], fetch=lambda _url: None)
    assert captured == {"name": "chatgpt_plan", "user_id": "alice"}


def test_someone_elses_plan_job_cannot_be_retried(client, db, fake):
    item = LinkSubmission(
        url="https://example.com/a",
        submitted_by="alice",
        provider_name="chatgpt_plan",
        status="failed",
        stage="failed",
    )
    db.add(item)
    db.commit()
    response = client.post(f"/api/v1/ingestion/links/{item.id}/retry")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CHATGPT_PLAN_OWNER_ONLY"


def test_provider_listing_reports_the_viewers_own_connection(client, fake):
    def plan_entry():
        listing = client.get("/api/v1/ai/providers").json()
        return next(item for item in listing if item["id"] == "chatgpt_plan")

    assert plan_entry()["configured"] is False
    connect(client, fake)
    assert plan_entry()["configured"] is True
    assert plan_entry()["chat_active"] is True
    assert "chatgpt_plan" in PROVIDERS


def test_graph_chat_tool_calls_run_on_the_plan(client, fake):
    connect(client, fake)
    fake.responses = [
        (
            200,
            completed(
                {
                    "reply": "",
                    "tool_calls": [{"name": "search_graph", "arguments_json": '{"q": "agents"}'}],
                }
            ),
        )
    ]
    runtime = graph_chat_provider("chatgpt_plan")
    response = runtime.respond(
        input_items=[{"role": "user", "content": "Tìm agent"}],
        tools=[{"name": "search_graph", "description": "Search", "parameters": {}}],
        instructions="Use tools.",
        metadata={},
    )
    assert [(call.name, call.arguments) for call in response.tool_calls] == [
        ("search_graph", {"q": "agents"})
    ]
    assert response.usage["input_tokens"] == 12


def test_partner_mode_uses_discovery_and_confidential_client(client, fake, monkeypatch):
    monkeypatch.setattr(settings, "chatgpt_plan_client_id", ISSUED)
    monkeypatch.setattr(settings, "chatgpt_plan_client_secret", SecretStr("partner-secret"))
    monkeypatch.setattr(
        settings, "chatgpt_plan_redirect_uri", "https://research.example.com/account/ai/callback"
    )
    params = start(client, fake)
    assert params["client_id"] == ISSUED
    assert "ext_agent_host_id" not in params and "agent_name_hint" not in params
    assert params["redirect_uri"] == "https://research.example.com/account/ai/callback"

    response = client.post(
        "/api/v1/ai-connections/chatgpt/complete",
        json={"state": params["state"], "code": "code-1"},
    )
    assert response.status_code == 200, response.text
    token_request = next(r for r in fake.requests if r.url.path == "/oauth/token")
    expected = base64.b64encode(f"{ISSUED}:partner-secret".encode()).decode()
    assert token_request.headers["authorization"] == f"Basic {expected}"


def test_access_log_never_records_the_authorization_code():
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:5000", "GET", "/auth/callback?code=secret-code&state=s", "1.1", 303),
        None,
    )
    OAuthCallbackLogFilter().filter(record)
    assert "secret-code" not in record.getMessage()


def test_enabling_plan_usage_requires_an_encryption_key():
    with pytest.raises(ValueError, match="CREDENTIALS_ENCRYPTION_KEY"):
        Settings(chatgpt_plan_enabled=True, credentials_encryption_key=None)


def test_disabled_feature_reports_status_but_refuses_to_start(client):
    status = client.get("/api/v1/ai-connections/chatgpt").json()
    assert status["enabled"] is False and status["status"] == "not_connected"
    response = client.post("/api/v1/ai-connections/chatgpt/start")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "CHATGPT_PLAN_DISABLED"
