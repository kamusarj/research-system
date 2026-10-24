"""A misconfigured provider should be visible before a submission depends on it.

The provider listing reported `reachable: null` for every hosted provider, so a wrong or
expired key stayed invisible until a source had already been fetched, classified and
failed with an authentication error.
"""

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import settings
from app.services import ai
from app.services.ai import preflight_provider, provider_status, reset_provider_preflight_cache


@pytest.fixture(autouse=True)
def clear_preflight_cache():
    reset_provider_preflight_cache()
    yield
    reset_provider_preflight_cache()


def _respond(monkeypatch, status_code: int, *, capture: dict | None = None):
    def fake_get(url, headers=None, params=None, timeout=None):
        if capture is not None:
            capture.update({"url": url, "headers": headers or {}, "params": params or {}})
        return httpx.Response(status_code, request=httpx.Request("GET", url))

    monkeypatch.setattr(ai.httpx, "get", fake_get)


def test_a_working_credential_is_reported_as_answering(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", SecretStr("key-that-works"))
    _respond(monkeypatch, 200)

    assert preflight_provider("deepseek") is True


def test_a_rejected_credential_is_reported_as_not_answering(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", SecretStr("key-that-expired"))
    _respond(monkeypatch, 401)

    # This is exactly the failure the preflight exists to surface early.
    assert preflight_provider("openai") is False


def test_an_unreachable_host_is_reported_as_not_answering(monkeypatch):
    monkeypatch.setattr(settings, "mistral_api_key", SecretStr("key"))

    def fail(*_args, **_kwargs):
        raise httpx.ConnectError("no route to host")

    monkeypatch.setattr(ai.httpx, "get", fail)

    assert preflight_provider("mistral") is False


def test_an_unconfigured_provider_is_not_contacted(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", None)

    def fail(*_args, **_kwargs):
        raise AssertionError("an unconfigured provider must never be contacted")

    monkeypatch.setattr(ai.httpx, "get", fail)

    # Null means "nothing to test", which is different from "tested and failed".
    assert preflight_provider("gemini") is None


def test_the_credential_travels_in_the_request_and_not_in_the_result(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", SecretStr("secret-key-marker"))
    capture: dict = {}
    _respond(monkeypatch, 200, capture=capture)

    result = preflight_provider("deepseek")

    assert capture["headers"]["Authorization"] == "Bearer secret-key-marker"
    assert result is True
    assert "secret-key-marker" not in str(result)


def test_a_repeated_check_reuses_the_recent_result(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", SecretStr("key"))
    calls: list[str] = []

    def counting_get(url, headers=None, params=None, timeout=None):
        calls.append(url)
        return httpx.Response(200, request=httpx.Request("GET", url))

    monkeypatch.setattr(ai.httpx, "get", counting_get)

    preflight_provider("deepseek")
    preflight_provider("deepseek")

    # A polling UI must not multiply requests against the provider.
    assert len(calls) == 1


def test_the_listing_does_not_contact_providers_unless_asked(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", SecretStr("key"))

    def fail(*_args, **_kwargs):
        raise AssertionError("the default listing must stay free of network calls")

    monkeypatch.setattr(ai.httpx, "get", fail)
    monkeypatch.setattr(ai, "ollama_reachable", lambda: False)

    statuses = {item["id"]: item for item in provider_status()}

    assert statuses["deepseek"]["reachable"] is None


def test_the_listing_reports_preflight_results_when_asked(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", SecretStr("key"))
    _respond(monkeypatch, 200)
    monkeypatch.setattr(ai, "ollama_reachable", lambda: False)

    statuses = {item["id"]: item for item in provider_status(preflight=True)}

    assert statuses["deepseek"]["reachable"] is True
    assert statuses["ollama"]["reachable"] is False


def test_the_api_never_returns_a_key(client, monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", SecretStr("secret-key-marker"))
    _respond(monkeypatch, 200)
    monkeypatch.setattr(ai, "ollama_reachable", lambda: True)

    response = client.get("/api/v1/ai/providers?preflight=true")

    assert response.status_code == 200
    assert "secret-key-marker" not in response.text
