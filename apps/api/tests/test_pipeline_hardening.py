from datetime import timedelta

import httpx
import pytest

from app.core.config import settings
from app.models import LinkSubmission, ResearchItem, utcnow
from app.services.ingestion import claim_next_submission, run_pending_submissions
from app.services.sources import http as source_http
from app.services.sources.errors import SourceError
from tests.test_ingestion import result


def queue_reviewable_link(client, db, monkeypatch, url: str = "https://example.com/agent"):
    monkeypatch.setattr(
        "app.services.ingestion.fetch_url",
        lambda _url, on_stage: result(url, "Agent note", "An AI agent pattern for support."),
    )
    response = client.post("/api/v1/ingestion/links", json={"url": url, "provider": "mistral"})
    assert response.status_code == 202, response.text
    assert run_pending_submissions(db) == 1
    item = db.get(LinkSubmission, response.json()["id"])
    assert item.review_status == "needs_review"
    return item


def test_failed_approval_publishes_nothing_and_can_be_retried(client, db, monkeypatch):
    item = queue_reviewable_link(client, db, monkeypatch)

    from app.services import link_mapping

    original = link_mapping.create_link_change_set

    def broken_change_set(*_args, **_kwargs):
        raise RuntimeError("graph proposal failed")

    monkeypatch.setattr(link_mapping, "create_link_change_set", broken_change_set)
    failed = client.post(f"/api/v1/ingestion/links/{item.id}/approve", json={})
    db.rollback()

    assert failed.status_code == 500
    assert db.query(ResearchItem).count() == 0
    db.refresh(item)
    assert item.review_status == "needs_review"

    monkeypatch.setattr(link_mapping, "create_link_change_set", original)
    approved = client.post(f"/api/v1/ingestion/links/{item.id}/approve", json={})
    repeated = client.post(f"/api/v1/ingestion/links/{item.id}/approve", json={})

    assert approved.status_code == 200, approved.text
    assert repeated.status_code == 409
    assert db.query(ResearchItem).count() == 1


def test_expired_lease_is_not_reclaimed_after_the_last_attempt(db):
    item = LinkSubmission(
        url="https://example.com/crashes-the-worker",
        source_type="manual",
        provider_name="mistral",
        status="analyzing",
        stage="analyzing",
        attempt_count=settings.intake_max_attempts,
        next_attempt_at=utcnow() - timedelta(seconds=1),
    )
    db.add(item)
    db.commit()

    assert claim_next_submission(db) is None
    db.refresh(item)
    assert item.status == "failed"
    assert item.error_code == "WORKER_LEASE_EXPIRED"


def test_slow_drip_source_hits_the_total_deadline(monkeypatch):
    monkeypatch.setattr(settings, "intake_request_timeout_seconds", 0.05)
    monkeypatch.setattr(settings, "intake_request_retries", 0)
    monkeypatch.setattr(source_http, "validate_public_url", lambda _url: None)
    monkeypatch.setattr(source_http, "assert_peer_is_public", lambda _response: None)

    class SlowStream(httpx.SyncByteStream):
        def __iter__(self):
            import time

            for _ in range(50):
                time.sleep(0.01)
                yield b"x"

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, headers={"content-type": "text/html"}, stream=SlowStream()
        )
    )
    real_client = httpx.Client
    monkeypatch.setattr(
        source_http.httpx,
        "Client",
        lambda **kwargs: real_client(**{**kwargs, "transport": transport}),
    )

    with pytest.raises(SourceError) as raised:
        source_http.fetch_public("https://example.com/slow", {"text/html"})

    assert raised.value.code == "FETCH_TIMEOUT"


def test_collector_refuses_internal_feed_urls_without_leaking_errors(client):
    source = client.post(
        "/api/v1/collector/sources",
        json={
            "key": "internal",
            "name": "Internal",
            "type": "rss",
            "url": "http://127.0.0.1:5432/feed.xml",
        },
    )
    assert source.status_code == 201, source.text

    run = client.post(f"/api/v1/collector/sources/{source.json()['id']}/run").json()

    assert run["status"] == "failed"
    assert run["error"] == "INVALID_URL"


def test_duplicate_of_a_rejected_original_is_reprocessed_on_resubmit(client, db, monkeypatch):
    original = queue_reviewable_link(client, db, monkeypatch, "https://example.com/original")
    monkeypatch.setattr(
        "app.services.ingestion.fetch_url",
        lambda _url, on_stage: result(
            "https://example.com/original", "Agent note", "An AI agent pattern for support."
        ),
    )
    mirror = client.post(
        "/api/v1/ingestion/links", json={"url": "https://mirror.example.com/copy"}
    ).json()
    assert run_pending_submissions(db) == 1
    stored = db.get(LinkSubmission, mirror["id"])
    assert stored.review_status == "duplicate"

    assert client.post(f"/api/v1/ingestion/links/{original.id}/reject").status_code == 200
    again = client.post("/api/v1/ingestion/links", json={"url": "https://mirror.example.com/copy"})

    assert again.status_code == 202
    db.refresh(stored)
    assert stored.status == "pending"
    assert stored.duplicate_of_id is None
    receipt = client.get(f"/api/v1/intake/receipts/{again.json()['receipt_id']}").json()
    assert receipt["status"] == "queued"


def test_enrichment_provider_rate_limit_is_a_typed_error(client, monkeypatch):
    created = client.post(
        "/api/v1/research", json={"title": "Agent memory", "content": "Some content"}
    ).json()

    class RateLimitedProvider:
        name = "mistral"
        version = "test"

        def enrich(self, _title, _content):
            request = httpx.Request("POST", "https://api.mistral.ai/v1/chat/completions")
            raise httpx.HTTPStatusError(
                "rate limited", request=request, response=httpx.Response(429, request=request)
            )

    monkeypatch.setattr("app.services.ai.provider", lambda _name=None, **_kw: RateLimitedProvider())

    response = client.post(f"/api/v1/ai/enrich/{created['id']}")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_PROVIDER_RATE_LIMITED"
