import asyncio
import contextvars
import json
import socketserver
import ssl
import threading
import time
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from pydantic import BaseModel, ConfigDict, SecretStr

from app.core.config import settings
from app.services import ai
from app.services.ai_usage import collect_usage
from app.services.object_storage import DocumentError
from app.services.providers import local_models
from app.services.providers.local_models import (
    LOCAL_PROVIDERS,
    LocalGraphChatProvider,
    complete_local_json,
    list_local_models,
)


class StructuredAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str
    count: int


@pytest.fixture(autouse=True)
def configured_models(monkeypatch):
    monkeypatch.setattr(settings, "ollama_base_url", "http://ollama.fixture.test:11434")
    monkeypatch.setattr(settings, "ollama_model", "installed:latest")
    monkeypatch.setattr(settings, "ollama_api_key", SecretStr("fixture-only"))
    monkeypatch.setattr(settings, "local_openai_base_url", "https://lm.fixture.test/v1")
    monkeypatch.setattr(settings, "local_openai_model", "installed-model")
    monkeypatch.setattr(settings, "local_openai_api_key", SecretStr("fixture-only"))
    monkeypatch.setattr(settings, "local_ai_max_response_bytes", 2_000_000)
    monkeypatch.setattr(settings, "ai_request_timeout", 120.0)


def mock_server(monkeypatch, handler):
    real_client = httpx.AsyncClient
    requests = []
    clients = []

    def observed(request):
        requests.append(request)
        return handler(request)

    def factory(**kwargs):
        clients.append(kwargs)
        return real_client(transport=httpx.MockTransport(observed), **kwargs)

    monkeypatch.setattr(local_models.httpx, "AsyncClient", factory)
    return requests, clients


def completion(provider, content, *, usage=None):
    if provider == "ollama":
        return {
            "message": {"role": "assistant", "content": content},
            "done": True,
            **({"prompt_eval_count": 7, "eval_count": 3} if usage is None else usage),
        }
    return {
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {
            "prompt_tokens": 7,
            "completion_tokens": 3,
            "prompt_tokens_details": {"cached_tokens": 2},
        }
        if usage is None
        else usage,
    }


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
def test_json_inference_uses_fixed_endpoint_schema_server_key_and_bounds(monkeypatch, provider):
    output = {"answer": "A bounded local answer", "count": 2}
    requests, clients = mock_server(
        monkeypatch,
        lambda _request: httpx.Response(
            200,
            json=completion(provider, json.dumps(output)),
        ),
    )

    result, usage = complete_local_json(provider, "Synthetic prompt", StructuredAnswer, 64)

    assert result == output
    assert usage["input_tokens"] == 7 and usage["output_tokens"] == 3
    assert usage["total_tokens"] == 10
    assert clients[0]["trust_env"] is False
    assert clients[0]["follow_redirects"] is False
    assert clients[0]["timeout"].read == 120
    assert requests[0].headers["Authorization"] == "Bearer fixture-only"
    assert requests[0].headers["Accept-Encoding"] == "identity"
    payload = json.loads(requests[0].content)
    assert payload["stream"] is False
    assert payload["messages"][1]["content"] == "Synthetic prompt"
    assert "fixture-only" not in json.dumps((result, usage))
    if provider == "ollama":
        assert str(requests[0].url) == "http://ollama.fixture.test:11434/api/chat"
        assert payload["model"] == "installed:latest"
        assert payload["format"] == StructuredAnswer.model_json_schema()
        assert payload["think"] is False
        assert payload["options"] == {"temperature": 0, "num_predict": 64}
    else:
        assert str(requests[0].url) == "https://lm.fixture.test/v1/chat/completions"
        assert payload["model"] == "installed-model"
        assert payload["response_format"]["json_schema"]["schema"] == (
            StructuredAnswer.model_json_schema()
        )
        assert payload["response_format"]["json_schema"]["strict"] is True
        assert payload["max_tokens"] == 64
        assert usage["cached_input_tokens"] == 2


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
def test_explicit_model_is_pinned_without_altering_server_default(monkeypatch, provider):
    requests, _ = mock_server(
        monkeypatch,
        lambda _request: httpx.Response(
            200,
            json=completion(provider, '{"answer":"ok","count":1}'),
        ),
    )
    complete_local_json(provider, "Prompt", StructuredAnswer, 64, model="pinned-model")
    assert json.loads(requests[0].content)["model"] == "pinned-model"
    assert getattr(settings, f"{provider}_model") != "pinned-model"


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
def test_inventory_filters_deduplicates_caps_and_never_paginates(monkeypatch, provider):
    name_key = "name" if provider == "ollama" else "id"
    items = [
        {name_key: value}
        for value in [
            "z-model",
            "a-model",
            "a-model",
            "",
            " leading space",
            "x" * 201,
            *[f"model-{index}" for index in range(250)],
        ]
    ]
    payload = {"models" if provider == "ollama" else "data": items, "next": "http://unsafe.test/"}
    requests, clients = mock_server(monkeypatch, lambda _request: httpx.Response(200, json=payload))

    result = list_local_models(provider, timeout=0.75)

    assert len(result) == 200
    assert len(set(result)) == 200
    assert result == sorted(result)
    assert all(local_models._MODEL.fullmatch(value) for value in result)
    assert requests[0].method == "GET" and len(requests) == 1
    assert requests[0].url.path == ("/api/tags" if provider == "ollama" else "/v1/models")
    assert clients[0]["timeout"].read == 0.75


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
def test_empty_inventory_is_not_a_fake_model_or_a_download(monkeypatch, provider):
    requests, _ = mock_server(
        monkeypatch,
        lambda _request: httpx.Response(
            200,
            json={"models" if provider == "ollama" else "data": []},
        ),
    )
    assert list_local_models(provider) == []
    assert len(requests) == 1
    assert requests[0].method == "GET"


def test_ollama_inventory_supports_model_field_and_optional_auth(monkeypatch):
    monkeypatch.setattr(settings, "ollama_api_key", None)
    requests, _ = mock_server(
        monkeypatch,
        lambda _request: httpx.Response(
            200,
            json={"models": [{"model": "model:quantized"}]},
        ),
    )
    assert list_local_models("ollama") == ["model:quantized"]
    assert "Authorization" not in requests[0].headers


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
@pytest.mark.parametrize(
    "content",
    [
        '```json\n{"answer":"ok","count":1}\n```',
        '{"answer":"ok","count":"1"}',
        '{"answer":"ok","count":1,"extra":true}',
        '{"answer":"ok"}',
        "[]",
        '{"answer":"ok","count":1,"count":2}',
        '{"answer":"ok","count":NaN}',
    ],
)
def test_json_output_must_match_strict_schema(monkeypatch, provider, content):
    mock_server(
        monkeypatch,
        lambda _request: httpx.Response(
            200,
            json=completion(provider, content),
        ),
    )
    with pytest.raises(DocumentError) as error:
        complete_local_json(provider, "Prompt", StructuredAnswer, 64)
    assert error.value.code == "CHAT_MODEL_INCOMPATIBLE"
    assert content not in str(error.value)


TOOLS = [
    {
        "type": "function",
        "name": "search_nodes",
        "description": "Find knowledge",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    }
]


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
def test_tool_envelope_round_trip_keeps_executor_in_control(monkeypatch, provider):
    responses = iter(
        [
            {
                "reply": "",
                "tool_calls": [{"name": "search_nodes", "arguments_json": '{"query":"ReAct"}'}],
            },
            {"reply": "Có nguồn đã kiểm chứng.", "tool_calls": []},
        ]
    )
    requests, _ = mock_server(
        monkeypatch,
        lambda _request: httpx.Response(
            200,
            json=completion(provider, json.dumps(next(responses))),
        ),
    )
    runtime = LocalGraphChatProvider(
        provider, model="pinned-model", timeout=20, max_output_tokens=128
    )
    items = [{"role": "user", "content": "ReAct là gì?"}]
    first = runtime.respond(
        input_items=items,
        tools=TOOLS,
        instructions="Use governed tools",
        metadata={"business_id": "private-fixture-id"},
    )
    assert first.tool_calls[0].arguments == {"query": "ReAct"}
    assert first.tool_calls[0].name == "search_nodes"
    assert first.usage["total_tokens"] == 10
    items += first.output_items
    items.append(
        {
            "type": "function_call_output",
            "call_id": first.tool_calls[0].call_id,
            "output": '{"nodes":[]}',
        }
    )
    second = runtime.respond(
        input_items=items, tools=TOOLS, instructions="Use governed tools", metadata={}
    )
    assert second.text == "Có nguồn đã kiểm chứng."
    assert second.tool_calls == []
    for request in requests:
        payload = json.loads(request.content)
        assert payload["model"] == "pinned-model"
        assert "tools" not in payload  # No native/provider tool execution.
        assert "private-fixture-id" not in request.content.decode()
    assert "TOOL RESULT" in json.loads(requests[1].content)["messages"][1]["content"]


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
@pytest.mark.parametrize(
    ("output", "code"),
    [
        (
            {"reply": "ok", "tool_calls": [{"name": "publish", "arguments_json": "{}"}]},
            "CHAT_TOOL_VALIDATION_FAILED",
        ),
        (
            {"reply": "ok", "tool_calls": [{"name": "search_nodes", "arguments_json": "[]"}]},
            "CHAT_TOOL_VALIDATION_FAILED",
        ),
        (
            {"reply": "ok", "tool_calls": [{"name": "search_nodes", "arguments_json": "bad"}]},
            "CHAT_TOOL_VALIDATION_FAILED",
        ),
        ({"reply": "ok", "tool_calls": [], "extra": "ignored?"}, "CHAT_PROVIDER_FAILED"),
        ({"reply": 1, "tool_calls": []}, "CHAT_PROVIDER_FAILED"),
        ({"reply": "ok"}, "CHAT_PROVIDER_FAILED"),
        ({"reply": "", "tool_calls": []}, "CHAT_PROVIDER_FAILED"),
    ],
)
def test_unknown_tools_invalid_arguments_and_malformed_envelopes_fail_closed(
    monkeypatch,
    provider,
    output,
    code,
):
    mock_server(
        monkeypatch,
        lambda _request: httpx.Response(
            200,
            json=completion(provider, json.dumps(output)),
        ),
    )
    with pytest.raises(DocumentError) as error:
        LocalGraphChatProvider(provider).respond(
            input_items=[],
            tools=TOOLS,
            instructions="Governed",
            metadata={},
        )
    assert error.value.code == code


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
def test_probe_uses_short_budget_and_refuses_calls_when_no_tools_are_allowed(monkeypatch, provider):
    output = {"reply": "ok", "tool_calls": [{"name": "search_nodes", "arguments_json": "{}"}]}
    requests, clients = mock_server(
        monkeypatch,
        lambda _request: httpx.Response(
            200,
            json=completion(provider, json.dumps(output)),
        ),
    )
    with pytest.raises(DocumentError) as error:
        LocalGraphChatProvider(provider, max_output_tokens=128, timeout=20).respond(
            input_items=[],
            tools=[],
            instructions="Probe",
            metadata={},
        )
    assert error.value.code == "CHAT_TOOL_VALIDATION_FAILED"
    assert clients[0]["timeout"].read == 20
    payload = json.loads(requests[0].content)
    assert (
        payload["options"]["num_predict"] if provider == "ollama" else payload["max_tokens"]
    ) == 128


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
def test_browser_key_overrides_are_never_accepted(monkeypatch, provider):
    requests, _ = mock_server(monkeypatch, lambda _request: pytest.fail("Must not contact server"))
    with pytest.raises(DocumentError):
        LocalGraphChatProvider(provider, api_key=SecretStr("browser-fixture"))
    assert requests == []


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
@pytest.mark.parametrize(
    ("status", "code", "http_status"),
    [
        (301, "CHAT_PROVIDER_FAILED", 502),
        (401, "CHAT_API_KEY_INVALID", 422),
        (403, "CHAT_API_ACCESS_DENIED", 422),
        (404, "CHAT_MODEL_UNAVAILABLE", 422),
        (400, "CHAT_MODEL_INCOMPATIBLE", 422),
        (422, "CHAT_MODEL_INCOMPATIBLE", 422),
        (429, "CHAT_PROVIDER_RATE_LIMITED", 429),
        (500, "CHAT_PROVIDER_UNAVAILABLE", 503),
    ],
)
def test_error_bodies_urls_and_keys_are_never_exposed_or_redirected(
    monkeypatch,
    provider,
    status,
    code,
    http_status,
    caplog,
):
    requests, _ = mock_server(
        monkeypatch,
        lambda _request: httpx.Response(
            status,
            json={"error": {"message": "fixture-only https://private.fixture.test/"}},
            headers={"Location": "https://another.fixture.test/"},
        ),
    )
    with pytest.raises(DocumentError) as error:
        complete_local_json(provider, "Prompt", StructuredAnswer, 64)
    assert error.value.code == code
    assert error.value.status_code == http_status
    assert len(requests) == 1
    visible = str(error.value) + caplog.text
    assert "fixture-only" not in visible and "private.fixture.test" not in visible
    assert "another.fixture.test" not in visible


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
@pytest.mark.parametrize(
    ("exception", "code"),
    [
        (httpx.ReadTimeout, "CHAT_PROVIDER_TIMEOUT"),
        (httpx.ConnectError, "CHAT_PROVIDER_UNAVAILABLE"),
    ],
)
def test_transport_failures_are_sanitized(monkeypatch, provider, exception, code):
    def failure(request):
        raise exception("fixture-only private endpoint", request=request)

    mock_server(monkeypatch, failure)
    with pytest.raises(DocumentError) as error:
        list_local_models(provider)
    assert error.value.code == code
    assert "fixture-only" not in str(error.value)
    assert "private endpoint" not in str(error.value)


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
def test_oversized_declared_body_is_rejected_before_parsing(monkeypatch, provider):
    monkeypatch.setattr(settings, "local_ai_max_response_bytes", 1024)
    mock_server(
        monkeypatch,
        lambda _request: httpx.Response(
            200,
            content=b"{}",
            headers={"Content-Length": "1000000"},
        ),
    )
    with pytest.raises(DocumentError) as error:
        list_local_models(provider)
    assert error.value.code == "CHAT_PROVIDER_FAILED"


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
def test_streaming_body_is_bounded_without_content_length(monkeypatch, provider):
    class LargeStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"{" + b"x" * 1024
            pytest.fail("Reader must stop when the byte limit is exceeded")

    monkeypatch.setattr(settings, "local_ai_max_response_bytes", 1024)
    mock_server(monkeypatch, lambda _request: httpx.Response(200, stream=LargeStream()))
    with pytest.raises(DocumentError):
        list_local_models(provider)


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
def test_request_body_limit_prevents_any_network_call(monkeypatch, provider):
    monkeypatch.setattr(settings, "local_ai_max_response_bytes", 1024)
    requests, _ = mock_server(monkeypatch, lambda _request: pytest.fail("Oversized request"))
    with pytest.raises(DocumentError) as error:
        complete_local_json(provider, "x" * 2048, StructuredAnswer, 64)
    assert error.value.status_code == 413
    assert requests == []


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
def test_server_cannot_echo_its_authorization_key_in_output(monkeypatch, provider):
    mock_server(
        monkeypatch,
        lambda _request: httpx.Response(
            200,
            json=completion(provider, '{"answer":"fixture-only","count":1}'),
        ),
    )
    with pytest.raises(DocumentError) as error:
        complete_local_json(provider, "Prompt", StructuredAnswer, 64)
    assert "fixture-only" not in str(error.value)


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
@pytest.mark.parametrize(
    "base",
    [
        "",
        "file:///tmp/model",
        "https://key@private.fixture.test",
        "https://private.fixture.test/?key=fixture-only",
    ],
)
def test_invalid_static_configuration_is_rejected_without_contact(monkeypatch, provider, base):
    monkeypatch.setattr(settings, f"{provider}_base_url", base)
    requests, _ = mock_server(monkeypatch, lambda _request: pytest.fail("Invalid config"))
    with pytest.raises(DocumentError):
        list_local_models(provider)
    assert requests == []


def test_unknown_provider_and_invalid_model_never_contact_server(monkeypatch):
    requests, _ = mock_server(monkeypatch, lambda _request: pytest.fail("Invalid input"))
    with pytest.raises(DocumentError):
        list_local_models("openai")
    with pytest.raises(DocumentError):
        LocalGraphChatProvider("ollama", model="model\nheader")
    assert requests == []


def escaped(value):
    return "".join(f"\\u{ord(char):04x}" for char in value)


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
@pytest.mark.parametrize("field", ["answer", "property"])
def test_decoded_structured_values_and_property_names_cannot_echo_server_key(
    monkeypatch, provider, field, caplog
):
    secret = "arbitrary-local-token"
    monkeypatch.setattr(settings, f"{provider}_api_key", SecretStr(secret))
    content = (
        '{"answer":"' + escaped(secret) + '","count":1}'
        if field == "answer"
        else '{"answer":"ok","count":1,"' + escaped(secret) + '":"value"}'
    )
    mock_server(
        monkeypatch,
        lambda _: httpx.Response(200, json=completion(provider, content)),
    )
    with pytest.raises(DocumentError) as error:
        complete_local_json(provider, "Synthetic", StructuredAnswer, 64)
    assert error.value.code == "CHAT_PROVIDER_FAILED"
    assert secret not in str(error.value) + caplog.text


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
@pytest.mark.parametrize("location", ["reply", "argument-value", "argument-property"])
def test_each_nested_json_layer_is_checked_before_chat_text_or_tools_escape(
    monkeypatch, provider, location, caplog
):
    secret = "arbitrary-local-token"
    monkeypatch.setattr(settings, f"{provider}_api_key", SecretStr(secret))
    if location == "reply":
        content = '{"reply":"' + escaped(secret) + '","tool_calls":[]}'
    else:
        arguments = (
            '{"query":"' + escaped(secret) + '"}'
            if location == "argument-value"
            else '{"' + escaped(secret) + '":"value"}'
        )
        content = json.dumps(
            {"reply": "ok", "tool_calls": [{"name": "search_nodes", "arguments_json": arguments}]}
        )
    mock_server(
        monkeypatch, lambda _: httpx.Response(200, json=completion(provider, content))
    )
    with pytest.raises(DocumentError) as error:
        LocalGraphChatProvider(provider).respond(
            input_items=[], tools=TOOLS, instructions="Synthetic", metadata={}
        )
    assert error.value.code == "CHAT_PROVIDER_FAILED"
    assert secret not in str(error.value) + caplog.text


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
def test_unicode_escaped_inventory_cannot_return_server_key_as_model_id(monkeypatch, provider):
    secret = "arbitrary-local-token"
    monkeypatch.setattr(settings, f"{provider}_api_key", SecretStr(secret))
    collection, field = ("models", "name") if provider == "ollama" else ("data", "id")
    body = '{"' + collection + '":[{"' + field + '":"' + escaped(secret) + '"}]}'
    mock_server(monkeypatch, lambda _: httpx.Response(200, content=body.encode()))
    with pytest.raises(DocumentError) as error:
        list_local_models(provider)
    assert error.value.code == "CHAT_PROVIDER_FAILED"
    assert secret not in str(error.value)


def test_sync_adapter_can_run_inside_event_loop_without_losing_usage_context(monkeypatch):
    context = contextvars.ContextVar("local-model-test-context")
    context.set("synthetic-attempt")
    seen = []

    def handler(_):
        seen.append(context.get())
        return httpx.Response(200, json={"models": [{"name": "installed"}]})

    mock_server(monkeypatch, handler)

    async def caller():
        return list_local_models("ollama")

    assert asyncio.run(caller()) == ["installed"]
    assert seen == ["synthetic-attempt"]


@pytest.mark.parametrize("stage", ["headers", "body"])
def test_total_deadline_cancels_real_slow_drip_http_response(monkeypatch, stage):
    disconnected = threading.Event()

    class SlowServer(socketserver.ThreadingTCPServer):
        daemon_threads = True
        allow_reuse_address = True

    class SlowHandler(socketserver.BaseRequestHandler):
        def handle(self):
            self.request.settimeout(1)
            request = b""
            while b"\r\n\r\n" not in request:
                request += self.request.recv(4096)
            try:
                self.request.sendall(b"HTTP/1.1 200 OK\r\n")
                if stage == "body":
                    self.request.sendall(b"Content-Length: 32\r\n\r\n{")
                for index in range(10):
                    time.sleep(0.06)
                    chunk = f"X-Delay-{index}: 1\r\n".encode() if stage == "headers" else b" "
                    self.request.sendall(chunk)
            except OSError:
                disconnected.set()

    with SlowServer(("127.0.0.1", 0), SlowHandler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        monkeypatch.setattr(settings, "ollama_base_url", f"http://127.0.0.1:{server.server_address[1]}")
        start = time.monotonic()
        try:
            with pytest.raises(DocumentError) as error:
                list_local_models("ollama", timeout=0.2)
            elapsed = time.monotonic() - start
            assert error.value.code == "CHAT_PROVIDER_TIMEOUT"
            assert error.value.status_code == 504
            assert elapsed < 0.4  # Header trickling used to extend this beyond 0.7s.
            assert disconnected.wait(0.4), "Timed-out connection must be closed"
        finally:
            server.shutdown()
            thread.join(timeout=1)


def test_dns_stall_obeys_total_deadline_without_unbounded_resolvers_or_late_http(monkeypatch):
    original_lookup = socketserver.socket.getaddrinfo
    release_dns = threading.Event()
    resolver_calls = []
    completed_lookups = []
    http_calls = []

    def stalled_dns(*args, **kwargs):
        resolver_calls.append(args[0])
        completed = threading.Event()
        completed_lookups.append(completed)
        try:
            release_dns.wait(2)
            return original_lookup("127.0.0.1", args[1], *args[2:], **kwargs)
        finally:
            completed.set()

    class Server(socketserver.ThreadingTCPServer):
        daemon_threads = True

    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            http_calls.append(True)

    with Server(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        monkeypatch.setattr(
            settings, "ollama_base_url", f"http://slow-dns.fixture.invalid:{server.server_address[1]}"
        )
        monkeypatch.setattr(local_models.socket, "getaddrinfo", stalled_dns)
        try:
            for _ in range(local_models._DNS_WORKERS + 1):
                started = time.monotonic()
                with pytest.raises(DocumentError) as error:
                    list_local_models("ollama", timeout=0.08)
                assert error.value.code == "CHAT_PROVIDER_TIMEOUT"
                assert time.monotonic() - started < 0.3
            assert len(resolver_calls) == local_models._DNS_WORKERS
        finally:
            release_dns.set()
            for completed in completed_lookups:
                assert completed.wait(1)
            server.shutdown()
            thread.join(timeout=1)
        assert http_calls == []  # DNS completing after cancellation must never start inference.


def test_bounded_dns_preserves_original_host_sni_and_certificate_verification(
    monkeypatch, tmp_path
):
    host = "local-model.fixture.invalid"
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, host)])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder().subject_name(name).issuer_name(name)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(host)]), critical=False)
        .sign(key, hashes.SHA256())
    )
    certificate_path, key_path = tmp_path / "certificate.pem", tmp_path / "key.pem"
    certificate_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(certificate_path, key_path)
    sni, requests = [], []
    server_context.set_servername_callback(lambda _socket, name, _context: sni.append(name))

    class Server(socketserver.ThreadingTCPServer):
        daemon_threads = True

    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            with server_context.wrap_socket(self.request, server_side=True) as connection:
                connection.settimeout(1)
                request = b""
                while b"\r\n\r\n" not in request:
                    request += connection.recv(4096)
                requests.append(request.decode())
                body = b'{"models":[{"name":"installed"}]}'
                connection.sendall(
                    b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(body)).encode()
                    + b"\r\nConnection: close\r\n\r\n" + body
                )

    real_client = httpx.AsyncClient
    client_context = ssl.create_default_context(cafile=certificate_path)
    monkeypatch.setattr(local_models.httpx, "AsyncClient", lambda **kw: real_client(
        verify=client_context, **kw
    ))
    lookup = local_models.socket.getaddrinfo
    monkeypatch.setattr(local_models.socket, "getaddrinfo", lambda _host, port, **kw: lookup(
        "127.0.0.1", port, **kw
    ))
    with Server(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        monkeypatch.setattr(settings, "ollama_base_url", f"https://{host}:{port}")
        try:
            assert list_local_models("ollama", timeout=1) == ["installed"]
        finally:
            server.shutdown()
            thread.join(timeout=1)
    assert client_context.check_hostname is True
    assert client_context.verify_mode == ssl.CERT_REQUIRED
    assert sni == [host]
    assert f"Host: {host}:{port}\r\n" in requests[0]


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
@pytest.mark.parametrize("content", ['{"answer":"ok","count":1}', "bad-json"])
def test_structured_usage_is_reported_exactly_once_even_when_decoding_fails(
    monkeypatch, provider, content
):
    mock_server(
        monkeypatch, lambda _: httpx.Response(200, json=completion(provider, content))
    )
    runtime = ai.OllamaProvider() if provider == "ollama" else ai.LocalOpenAIProvider()
    with collect_usage() as usage:
        if content == "bad-json":
            with pytest.raises(httpx.HTTPStatusError):
                runtime.complete_json("Synthetic prompt", StructuredAnswer)
        else:
            assert runtime.complete_json("Synthetic prompt", StructuredAnswer).answer == "ok"
    assert usage["input_tokens"] == 7
    assert usage["output_tokens"] == 3
    assert usage["total_tokens"] == 10
    assert usage["prompt_chars"] == len("Synthetic prompt")


@pytest.mark.parametrize("provider", sorted(LOCAL_PROVIDERS))
def test_graph_usage_is_returned_for_the_chat_caller_without_duplicate_observation(
    monkeypatch, provider
):
    mock_server(
        monkeypatch,
        lambda _: httpx.Response(
            200, json=completion(provider, '{"reply":"ok","tool_calls":[]}')
        ),
    )
    with collect_usage() as usage:
        response = LocalGraphChatProvider(provider).respond(
            input_items=[], tools=[], instructions="Synthetic", metadata={}
        )
    assert response.usage["total_tokens"] == 10
    assert usage == {}
