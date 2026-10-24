import pytest
from pydantic import BaseModel

from app.services import ai
from app.services.ai_output_guard import (
    REDACTION,
    credential_kinds,
    redact_credentials,
    reject_credentials,
)
from app.services.providers import cli_bridge

FAKE_JWT = "eyJhbGciOiJIUzI1NiJ9." + "a" * 30 + "." + "b" * 30


class Summary(BaseModel):
    summary: str


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        (FAKE_JWT, "jwt"),
        ("key sk-proj-" + "x" * 30, "openai-key"),
        ('"refresh_token": "' + "r" * 40 + '"', "oauth-field"),
        ("-----BEGIN PRIVATE KEY-----", "private-key"),
        ("AKIA" + "A" * 16, "aws-access-key"),
    ],
)
def test_credential_like_strings_are_detected_anywhere(text, kind):
    assert kind in credential_kinds({"nodes": [{"summary": f"prefix {text} suffix"}]})


def test_ordinary_research_text_passes():
    reject_credentials(
        {"summary": "OAuth 2.0 uses access tokens; this article explains token rotation."},
        provider="codex",
    )


def test_cli_completion_with_leaked_token_is_redacted(monkeypatch):
    monkeypatch.setattr(
        ai,
        "bridge_complete",
        lambda *_a, **_k: {"output": {"summary": f"see {FAKE_JWT} here"}, "usage": {}},
    )
    result = ai.CodexProvider().complete_json("prompt", Summary)
    assert FAKE_JWT not in result.summary
    assert result.summary == f"see {REDACTION} here"


def test_cli_chat_reply_with_leaked_token_is_redacted(monkeypatch):
    monkeypatch.setattr(
        cli_bridge,
        "bridge_complete",
        lambda *_a, **_k: {"output": {"reply": f"Here: {FAKE_JWT}", "tool_calls": []}},
    )
    monkeypatch.setattr(cli_bridge, "bridge_configured", lambda: True)
    response = cli_bridge.CliGraphChatProvider("codex").respond(
        input_items=[{"role": "user", "content": "hi"}], tools=[], instructions="x", metadata={}
    )
    assert FAKE_JWT not in response.text and REDACTION in response.text


def test_redaction_walks_nested_values():
    redacted = redact_credentials({"a": [{"b": FAKE_JWT}], "n": 3}, provider="codex")
    assert redacted == {"a": [{"b": REDACTION}], "n": 3}
