"""The app talks to subscription CLIs only through the host bridge.

Background tasks must keep their existing error semantics (auth, rate limit, timeout), and
graph chat must turn structured CLI replies into the same tool calls the API providers emit.
"""

import json

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import settings
from app.schemas.chat import ChatConnectionRequest
from app.schemas.ingestion import LinkClassification
from app.services import ai
from app.services.ai import _enrichment_error, preflight_provider, provider_status
from app.services.object_storage import DocumentError
from app.services.providers import cli_bridge
from app.services.providers.cli_bridge import CliGraphChatProvider
from app.services.providers.openai_graph_chat import graph_chat_provider

CLASSIFICATION = {
    "content_type": "paper",
    "language": "en",
    "summary": "ReAct interleaves reasoning and acting.",
    "relevance_score": 90,
    "confidence": 0.9,
    "reasoning": "Agent pattern paper.",
}


@pytest.fixture(autouse=True)
def bridge_settings(monkeypatch):
    monkeypatch.setattr(settings, "ai_cli_bridge_url", "http://172.17.0.1:11436")
    monkeypatch.setattr(settings, "ai_cli_bridge_token", SecretStr("b" * 40))
    ai.reset_provider_preflight_cache()
    yield
    ai.reset_provider_preflight_cache()


def _bridge(monkeypatch, *responses, capture: list | None = None):
    queue = list(responses)

    def fake_post(url, *, headers, json, timeout):
        if capture is not None:
            capture.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        status, payload = queue.pop(0)
        return httpx.Response(status, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(cli_bridge.httpx, "post", fake_post)


def test_codex_provider_sends_the_schema_and_validates_the_output(monkeypatch):
    sent: list = []
    _bridge(monkeypatch, (200, {"output": CLASSIFICATION, "usage": {}}), capture=sent)

    result = ai.CodexProvider().complete_json("Classify this link", LinkClassification)

    assert result.content_type == "paper" and result.tags == []
    body = sent[0]["json"]
    assert sent[0]["url"] == "http://172.17.0.1:11436/v1/complete"
    assert sent[0]["headers"]["Authorization"] == f"Bearer {'b' * 40}"
    assert body["backend"] == "codex"
    assert body["model"] == settings.codex_model and body["effort"] == settings.codex_effort
    assert body["schema"] == LinkClassification.model_json_schema()


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (429, "AI_PROVIDER_RATE_LIMITED"),
        (403, "AI_PROVIDER_AUTH_FAILED"),
        (504, "AI_PROVIDER_ERROR"),
    ],
)
def test_bridge_failures_keep_background_task_error_codes(monkeypatch, status, code):
    _bridge(monkeypatch, (status, {"error": {"code": "CLI_X", "message": "x"}}))

    with pytest.raises(httpx.HTTPStatusError) as error:
        ai.ClaudeCodeProvider().complete_json("Classify", LinkClassification)
    assert _enrichment_error(error.value).code == code


def test_cli_providers_are_listed_once_the_bridge_is_configured(monkeypatch):
    listed = {item["id"]: item for item in provider_status()}
    assert listed["codex"]["configured"] is True
    assert listed["antigravity"]["model"] == settings.antigravity_model

    monkeypatch.setattr(settings, "ai_cli_bridge_url", "")
    assert {item["id"]: item for item in provider_status()}["codex"]["configured"] is False


def test_preflight_asks_the_bridge_without_spending_quota(monkeypatch):
    calls: list[str] = []

    def fake_get(url, *, headers, timeout):
        calls.append(url)
        payload = {"backends": {"codex": {"available": True}, "antigravity": {"available": False}}}
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(cli_bridge.httpx, "get", fake_get)

    assert preflight_provider("codex") is True
    assert preflight_provider("antigravity") is False
    assert all(url.endswith("/v1/health") for url in calls)


def test_graph_chat_turns_structured_replies_into_tool_calls(monkeypatch):
    sent: list = []
    tool_reply = {
        "reply": "",
        "tool_calls": [{"name": "search_nodes", "arguments_json": '{"query": "ReAct"}'}],
    }
    _bridge(
        monkeypatch,
        (200, {"output": tool_reply, "usage": {"input_tokens": 10, "output_tokens": 4}}),
        (200, {"output": {"reply": "ReAct là một mẫu agent.", "tool_calls": []}, "usage": {}}),
        capture=sent,
    )
    runtime = graph_chat_provider("codex")
    tools = [
        {"type": "function", "name": "search_nodes", "description": "Search", "parameters": {}}
    ]
    items = [{"role": "user", "content": "ReAct là gì?"}]

    first = runtime.respond(input_items=items, tools=tools, instructions="Be helpful", metadata={})
    assert first.tool_calls[0].name == "search_nodes"
    assert first.tool_calls[0].arguments == {"query": "ReAct"}
    assert first.usage["total_tokens"] == 14

    items += first.output_items
    items.append(
        {
            "type": "function_call_output",
            "call_id": first.tool_calls[0].call_id,
            "output": '{"nodes": []}',
        }
    )
    second = runtime.respond(input_items=items, tools=tools, instructions="Be helpful", metadata={})

    assert second.text == "ReAct là một mẫu agent." and second.tool_calls == []
    prompt = sent[1]["json"]["prompt"]
    assert "TOOL RESULT" in prompt and first.tool_calls[0].call_id in prompt
    assert "search_nodes" in sent[0]["json"]["system"]
    assert sent[0]["json"]["schema"]["properties"]["tool_calls"]["items"]["properties"]["name"][
        "enum"
    ] == ["search_nodes"]


def test_brainstorm_without_tools_only_asks_for_a_reply(monkeypatch):
    sent: list = []
    _bridge(monkeypatch, (200, {"output": {"reply": "Ý tưởng"}, "usage": {}}), capture=sent)

    response = graph_chat_provider("claude_code").respond(
        input_items=[{"role": "user", "content": "Gợi ý?"}], tools=[], instructions="x", metadata={}
    )

    assert response.text == "Ý tưởng"
    assert list(sent[0]["json"]["schema"]["properties"]) == ["reply"]


@pytest.mark.parametrize(
    "tool_call",
    [
        {"name": "delete_everything", "arguments_json": "{}"},
        {"name": "search_nodes", "arguments_json": "not json"},
    ],
)
def test_graph_chat_rejects_unknown_tools_and_bad_arguments(monkeypatch, tool_call):
    _bridge(monkeypatch, (200, {"output": {"reply": "", "tool_calls": [tool_call]}}))
    tools = [{"name": "search_nodes", "parameters": {}}]

    with pytest.raises(DocumentError) as error:
        graph_chat_provider("codex").respond(
            input_items=[], tools=tools, instructions="x", metadata={}
        )
    assert error.value.code == "CHAT_TOOL_VALIDATION_FAILED"


@pytest.mark.parametrize(
    ("status", "bridge_code", "code"),
    [
        (429, "CLI_RATE_LIMITED", "CHAT_CLI_LIMIT_REACHED"),
        (403, "CLI_LOGIN_FAILED", "CHAT_CLI_LOGIN_REQUIRED"),
        (504, "CLI_TIMEOUT", "CHAT_PROVIDER_TIMEOUT"),
        (503, "CLI_BUSY", "CHAT_PROVIDER_UNAVAILABLE"),
    ],
)
def test_graph_chat_maps_bridge_errors(monkeypatch, status, bridge_code, code):
    _bridge(monkeypatch, (status, {"error": {"code": bridge_code, "message": "x"}}))

    with pytest.raises(DocumentError) as error:
        graph_chat_provider("antigravity").respond(
            input_items=[], tools=[], instructions="x", metadata={}
        )
    assert error.value.code == code


def test_an_unconfigured_bridge_is_unavailable_for_chat(monkeypatch):
    monkeypatch.setattr(settings, "ai_cli_bridge_token", None)

    with pytest.raises(DocumentError) as error:
        CliGraphChatProvider("codex").respond(
            input_items=[], tools=[], instructions="x", metadata={}
        )
    assert error.value.code == "CHAT_PROVIDER_UNAVAILABLE"


def test_cli_providers_never_take_personal_keys():
    with pytest.raises(DocumentError):
        graph_chat_provider("codex", api_key=SecretStr("sk-personal"), model="gpt")
    with pytest.raises(ValidationError):
        ChatConnectionRequest(
            provider="codex",
            credential_source="personal",
            model_name="gpt-6-luna",
            personal_api_key=SecretStr("sk-personal-key"),
        )
    assert ChatConnectionRequest(provider="codex").provider == "codex"


def test_bridge_payload_is_json_serialisable():
    schema = cli_bridge._response_schema(["a"])
    assert json.loads(json.dumps(schema))["required"] == ["reply", "tool_calls"]
