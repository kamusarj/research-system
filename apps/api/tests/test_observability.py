import json
import logging

from pydantic import SecretStr

from app.core.config import settings
from app.core.observability import (
    JsonLogFormatter,
    configure_logging,
    exception_fields,
    request_id_context,
    safe_request_id,
)


def test_request_id_validation_is_conservative():
    assert safe_request_id("edge-01:trace_2.3") == "edge-01:trace_2.3"

    generated = safe_request_id("bad id\nAuthorization: secret-marker")

    assert generated != "bad id\nAuthorization: secret-marker"
    assert len(generated) == 36


def test_json_formatter_uses_allowlist_and_omits_exception_and_arbitrary_fields():
    formatter = JsonLogFormatter()
    token = request_id_context.set("request-safe-1")
    try:
        record = logging.LogRecord(
            name="research.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="Safe event name",
            args=(),
            exc_info=(ValueError, ValueError("secret-exception-marker"), None),
        )
        record.action = "test.completed"
        record.authorization = "secret-header-marker"
        record.document_content = "secret-document-marker"

        payload = json.loads(formatter.format(record))
    finally:
        request_id_context.reset(token)

    assert payload["request_id"] == "request-safe-1"
    assert payload["action"] == "test.completed"
    serialized = json.dumps(payload)
    assert "secret-exception-marker" not in serialized
    assert "secret-header-marker" not in serialized
    assert "secret-document-marker" not in serialized


def test_exception_fields_describe_the_failure_without_its_message():
    def inner() -> None:
        raise ValueError("secret-exception-marker https://user:pass@internal/doc")

    try:
        inner()
    except ValueError as exc:
        fields = exception_fields(exc)

    assert fields["exception_type"] == "ValueError"
    assert "test_observability.py" in fields["exception_location"]
    assert "inner" in fields["exception_location"]
    serialized = json.dumps(fields)
    assert "secret-exception-marker" not in serialized
    assert "internal/doc" not in serialized


def test_exception_location_survives_the_json_formatter():
    formatter = JsonLogFormatter()
    try:
        raise RuntimeError("secret-exception-marker")
    except RuntimeError as exc:
        record = logging.LogRecord(
            name="research-worker",
            level=logging.WARNING,
            pathname=__file__,
            lineno=1,
            msg="Intake worker loop failed",
            args=(),
            exc_info=None,
        )
        for key, value in exception_fields(exc).items():
            setattr(record, key, value)

    payload = json.loads(formatter.format(record))

    assert payload["exception_type"] == "RuntimeError"
    assert "test_observability.py" in payload["exception_location"]
    assert "secret-exception-marker" not in json.dumps(payload)


def test_default_raw_url_loggers_are_suppressed():
    configure_logging()

    assert not logging.getLogger("httpx").isEnabledFor(logging.INFO)
    assert not logging.getLogger("httpcore").isEnabledFor(logging.INFO)
    assert not logging.getLogger("neo4j.notifications").isEnabledFor(logging.CRITICAL)
    assert logging.getLogger("uvicorn.access").disabled is True


def test_every_api_response_has_safe_request_id(client):
    accepted = client.get("/api/v1/health", headers={"X-Request-ID": "browser-request-17"})
    replaced = client.get(
        "/api/v1/health", headers={"X-Request-ID": "invalid request id"}
    )

    assert accepted.headers["X-Request-ID"] == "browser-request-17"
    assert replaced.headers["X-Request-ID"] != "invalid request id"
    assert len(replaced.headers["X-Request-ID"]) == 36


def test_unhandled_errors_keep_correlation_without_exposing_message(client, monkeypatch):
    def fail_safely(_db):
        raise ValueError("secret-runtime-marker")

    monkeypatch.setattr("app.api.system.check_graph_invariants", fail_safely)

    response = client.get(
        "/api/v1/system/readiness", headers={"X-Request-ID": "failed-request-9"}
    )

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "failed-request-9"
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "secret-runtime-marker" not in response.text


def test_metrics_are_disabled_by_default(client, monkeypatch):
    monkeypatch.setattr(settings, "metrics_enabled", False)

    response = client.get("/metrics")

    assert response.status_code == 404


def test_metrics_fail_closed_without_a_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "metrics_enabled", True)
    monkeypatch.setattr(settings, "metrics_bearer_token", None)

    response = client.get("/metrics")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "METRICS_NOT_CONFIGURED"


def test_metrics_require_bearer_and_use_route_templates(client, monkeypatch):
    test_secret = "integration-only-observability-value"
    monkeypatch.setattr(settings, "metrics_enabled", True)
    monkeypatch.setattr(settings, "metrics_bearer_token", SecretStr(test_secret))
    document_id = "4fb864b1-218a-48f4-934c-4f93c2cab429"

    unauthorized = client.get("/metrics")
    client.get(f"/api/v1/documents/{document_id}?token=secret-query-marker")
    authorized = client.get(
        "/metrics", headers={"Authorization": f"Bearer {test_secret}"}
    )

    assert unauthorized.status_code == 401
    assert unauthorized.headers["WWW-Authenticate"] == "Bearer"
    assert authorized.status_code == 200
    assert authorized.headers["content-type"].startswith("text/plain")
    body = authorized.text
    assert "research_http_requests_total" in body
    assert 'route="/api/v1/documents/{document_id}"' in body
    assert document_id not in body
    assert test_secret not in body
    assert "secret-query-marker" not in body
