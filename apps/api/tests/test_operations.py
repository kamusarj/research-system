import json
import sys

import pytest

from app.services.object_storage import DocumentError
from app.services.providers.openai_graph_chat import GraphProviderResponse


class ProbeRuntime:
    name = "openai"
    model = "test-openai-model"

    def __init__(self, error: DocumentError | None = None):
        self.error = error
        self.requests: list[dict] = []

    def respond(self, **kwargs):
        self.requests.append(kwargs)
        if self.error is not None:
            raise self.error
        return GraphProviderResponse(
            response_id="response-secret-value",
            request_id="request-secret-value",
            text="provider output must not be printed",
        )


def test_verify_openai_cli_reports_safe_readiness(monkeypatch, capsys):
    from app import operations

    runtime = ProbeRuntime()
    monkeypatch.setattr(operations, "graph_chat_provider", lambda _name: runtime)
    monkeypatch.setattr(sys, "argv", ["operations", "verify-openai"])

    operations.main()

    output = capsys.readouterr()
    result = json.loads(output.out)
    assert result == {
        "model": "test-openai-model",
        "output_present": True,
        "provider": "openai",
        "request_id_present": True,
        "response_id_present": True,
        "status": "ready",
    }
    assert output.err == ""
    assert "secret-value" not in output.out
    assert "provider output" not in output.out
    assert runtime.requests[0]["tools"] == []
    assert runtime.requests[0]["metadata"]["operation"] == "operator-preflight"


def test_verify_openai_cli_reports_typed_failure_without_details(monkeypatch, capsys):
    from app import operations

    runtime = ProbeRuntime(
        DocumentError(
            "CHAT_PROVIDER_UNAVAILABLE",
            "upstream details and credentials must not be printed",
            503,
        )
    )
    monkeypatch.setattr(operations, "graph_chat_provider", lambda _name: runtime)
    monkeypatch.setattr(sys, "argv", ["operations", "verify-openai"])

    with pytest.raises(SystemExit) as caught:
        operations.main()

    output = capsys.readouterr()
    result = json.loads(output.err)
    assert caught.value.code == 2
    assert result["status"] == "unavailable"
    assert result["provider"] == "openai"
    assert result["error_code"] == "CHAT_PROVIDER_UNAVAILABLE"
    assert output.out == ""
    assert "upstream details" not in output.err
    assert "credentials" not in output.err


def test_verify_chat_provider_uses_configured_deepseek_without_leaking(monkeypatch, capsys):
    from app import operations
    from app.core.config import settings

    runtime = ProbeRuntime()
    runtime.name = "deepseek"
    runtime.model = "test-deepseek-model"
    monkeypatch.setattr(settings, "graph_chat_default_provider", "deepseek")
    monkeypatch.setattr(operations, "graph_chat_provider", lambda _name: runtime)
    monkeypatch.setattr(sys, "argv", ["operations", "verify-chat-provider"])

    operations.main()

    output = capsys.readouterr()
    result = json.loads(output.out)
    assert result["provider"] == "deepseek"
    assert result["model"] == "test-deepseek-model"
    assert result["output_present"] is True
    assert "secret-value" not in output.out
    assert "provider output" not in output.out
