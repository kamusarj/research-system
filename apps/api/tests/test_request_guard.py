import pytest

from app.core.config import settings


@pytest.fixture
def guarded(monkeypatch):
    monkeypatch.setattr(settings, "api_trusted_hosts", "testserver")
    monkeypatch.setattr(settings, "api_cors_origins", "http://localhost:13000")


def test_rebound_host_is_rejected(client, guarded):
    response = client.get("/api/v1/health", headers={"Host": "attacker.example:18000"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "HOST_NOT_ALLOWED"


def test_proxy_forwarded_host_must_be_trusted(client, guarded):
    rebound = client.get(
        "/api/v1/health", headers={"Host": "api:8000", "X-Forwarded-Host": "attacker.example"}
    )
    assert rebound.status_code == 400

    tunnel_gate = client.get(
        "/api/v1/health", headers={"Host": "api:8000", "X-Forwarded-Host": "frontend:3000"}
    )
    assert tunnel_gate.status_code == 200

    local = client.get(
        "/api/v1/health", headers={"Host": "api:8000", "X-Forwarded-Host": "localhost:13000"}
    )
    assert local.status_code == 200


def test_cross_site_mutation_is_blocked_even_without_login(client, guarded):
    assert not settings.auth_enabled
    payload = {"urls": ["https://example.com/a"]}

    cross_site = client.post(
        "/api/v1/ingestion/links",
        json=payload,
        headers={"Sec-Fetch-Site": "cross-site", "Origin": "https://attacker.example"},
    )
    assert cross_site.status_code == 403
    assert cross_site.json()["error"]["code"] == "CROSS_SITE_REQUEST_BLOCKED"

    same_site = client.post(
        "/api/v1/ingestion/links", json=payload, headers={"Sec-Fetch-Site": "same-site"}
    )
    assert same_site.status_code == 403


def test_legacy_browser_origin_falls_back_to_host_allowlist(client, guarded):
    blocked = client.post(
        "/api/v1/research", json={}, headers={"Origin": "https://attacker.example"}
    )
    assert blocked.status_code == 403
    opaque = client.post("/api/v1/research", json={}, headers={"Origin": "null"})
    assert opaque.status_code == 403
    allowed = client.post("/api/v1/research", json={}, headers={"Origin": "http://localhost:13000"})
    assert allowed.status_code != 403


def test_same_origin_and_non_browser_requests_pass(client, guarded):
    same_origin = client.post(
        "/api/v1/research", json={}, headers={"Sec-Fetch-Site": "same-origin"}
    )
    assert same_origin.status_code != 403
    script = client.post("/api/v1/research", json={})
    assert script.status_code != 403
    reads = client.get("/api/v1/health", headers={"Sec-Fetch-Site": "cross-site"})
    assert reads.status_code == 200


def test_wildcard_disables_host_check(client, monkeypatch):
    monkeypatch.setattr(settings, "api_trusted_hosts", "*")
    response = client.get("/api/v1/health", headers={"Host": "anything.example"})
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("path", "bucket"),
    [
        ("/api/v1/ingestion/links", "link-intake"),
        ("/api/v1/ingestion/links/abc/retry", "link-intake"),
        ("/api/v1/documents/brainstorm", "document-brainstorm"),
        ("/api/v1/documents/abc/ai-edits", "document-ai-edit"),
        ("/api/v1/documents/abc/graph/research", "document-ai-analysis"),
        ("/api/v1/documents/abc/rag/rebuild", "document-ai-analysis"),
        ("/api/v1/collector/sources/abc/run", "collector-run"),
        ("/api/v1/research-runs", "research-run"),
        ("/api/v1/gaps/abc/research-run", "research-run"),
    ],
)
def test_ai_spending_routes_are_rate_limited(path, bucket):
    from app.core.runtime_controls import RATE_POLICIES

    matched = [
        policy.bucket
        for method, pattern, policy in RATE_POLICIES
        if method == "POST" and pattern.fullmatch(path)
    ]
    assert matched == [bucket]


def test_research_run_creation_hits_the_rate_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "research_agent_enabled", False)
    monkeypatch.setattr(settings, "rate_limit_research_runs_per_window", 2)
    statuses = [
        client.post(
            "/api/v1/research-runs", json={"question": "Tính năng đang tắt thì sao?"}
        ).status_code
        for _ in range(3)
    ]
    assert statuses[:2] == [503, 503]
    assert statuses[2] == 429
