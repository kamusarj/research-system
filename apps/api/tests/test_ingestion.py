import json
import ssl

import httpx
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.models import AuditEvent, GraphChangeSet, LinkSubmission
from app.schemas.source import NormalizedSource
from app.services.ingestion import FetchedSourceResult, _source_error, run_pending_submissions
from app.services.sources.base import RawSource
from app.services.sources.errors import SourceError


def result(url: str, title: str, content: str, *, partial: bool = False) -> FetchedSourceResult:
    return FetchedSourceResult(
        NormalizedSource(
            id="article:test",
            source_type="article",
            canonical_url=url,
            title=title,
            raw_text=content,
            collection_status="PARTIAL" if partial else "EXTRACTED",
            limitation_code="METADATA_ONLY" if partial else None,
            limitation_message="Only metadata was available" if partial else None,
        )
    )


def test_provider_registry_never_exposes_keys(client):
    response = client.get("/api/v1/ai/providers")
    assert response.status_code == 200
    providers = response.json()
    assert {item["id"] for item in providers} == {
        "ollama",
        "openai",
        "deepseek",
        "gemini",
        "openrouter",
        "mistral",
        "claude_code",
        "codex",
        "antigravity",
        "chatgpt_plan",
    }
    assert all("api_key" not in item for item in providers)
    assert "token" not in response.text.lower()
    assert all("reachable" in item for item in providers)
    assert [item["id"] for item in providers if item["chat_active"]] == ["deepseek"]


def test_mock_provider_is_rejected(client):
    response = client.post(
        "/api/v1/ingestion/links",
        json={"url": "https://example.com/no-fake-provider", "provider": "mock"},
    )
    assert response.status_code == 422


def test_full_pipeline_review_publish_and_typed_graph(client, db, monkeypatch):
    content = (
        "A LangGraph RAG agent helps customer service teams retrieve policies and automate "
        "repeatable support workflows with human approval and measurable operations outcomes."
    )
    monkeypatch.setattr(
        "app.services.ingestion.fetch_url",
        lambda _url, on_stage: (
            on_stage("fetching"),
            on_stage("extracting"),
            result(
                "https://example.com/langgraph-agent",
                "LangGraph support agent",
                content,
            ),
        )[-1],
    )
    response = client.post(
        "/api/v1/ingestion/links",
        json={"url": "https://example.com/langgraph-agent", "provider": "mistral"},
    )
    assert response.status_code == 202, response.text
    assert response.json()["status"] == "pending"

    assert run_pending_submissions(db) == 1
    submission = client.get("/api/v1/ingestion/links").json()[0]
    assert submission["status"] == "completed"
    assert submission["stage"] == "completed"
    assert submission["review_status"] == "needs_review"
    assert submission["attempt_count"] == 1
    assert submission["classification"]["confidence"] == 0.65
    assert submission["classification"]["summary"].startswith("A LangGraph RAG agent")
    assert "Return grounded structured JSON" not in submission["classification"]["summary"]

    approved = client.post(f"/api/v1/ingestion/links/{submission['id']}/approve", json={})
    assert approved.status_code == 200
    research_id = approved.json()["research_id"]
    research = client.get(f"/api/v1/research/{research_id}").json()
    assert research["status"] == "approved"
    assert research["metadata"]["link_submission_id"] == submission["id"]

    graph = client.get("/api/v1/graph").json()
    assert any(node["type"] == "Technology" for node in graph["nodes"])
    assert any(edge["type"] == "USES_TECH" for edge in graph["edges"])

    duplicate = client.post(
        "/api/v1/ingestion/links", json={"url": "https://example.com/langgraph-agent"}
    )
    assert duplicate.status_code == 200
    assert db.query(LinkSubmission).count() == 1


def test_discord_receipt_auto_approves_into_graph_and_reports_related_gap(client, db, monkeypatch):
    url = "https://example.com/discord-agent-memory"
    content = (
        "A business agent memory architecture stores approved evidence and retrieves it "
        "for customer service decisions with human oversight."
    )
    monkeypatch.setattr(settings, "intake_auto_approve_confidence", 0.6)
    monkeypatch.setattr(
        "app.services.ingestion.fetch_url",
        lambda _url, on_stage: (
            on_stage("fetching"),
            on_stage("extracting"),
            result(url, "Discord agent memory", content),
        )[-1],
    )
    created = client.post(
        "/api/v1/intake/receipts",
        json={
            "source": {
                "type": "discord",
                "namespace": "discord",
                "occurrence_ref": "discord-message-100",
                "container_ref": "discord-channel-10",
                "metadata": {"schema_version": 1, "event_type": "message"},
            },
            "items": [
                {
                    "kind": "url",
                    "url": url,
                    "provider": "mistral",
                    "auto_approve": True,
                }
            ],
        },
    )

    assert created.status_code == 202, created.text
    assert run_pending_submissions(db) == 1
    receipt = client.get(f"/api/v1/intake/receipts/{created.json()['id']}").json()
    item = receipt["items"][0]

    assert receipt["status"] == "approved"
    assert item["review_status"] == "approved"
    assert item["research_id"]
    assert [gap["concept_key"] for gap in item["knowledge_gaps"]] == ["business-agent"]
    assert db.query(GraphChangeSet).count() == 1
    graph = client.get("/api/v1/graph").json()
    assert item["research_id"] in {node["id"] for node in graph["nodes"]}


def test_integration_pipeline_detects_extracts_analyzes_and_persists(client, db, monkeypatch):
    html = b"""
    <html lang="en"><head><title>Production agent study</title>
    <meta name="description" content="Measured deployment findings."></head>
    <body><main><h1>Findings</h1>
    <p>LangGraph agents improved customer service retrieval with human review.</p>
    <p>The evaluation measured repeatability, latency, and operational outcomes.</p>
    </main></body></html>
    """
    monkeypatch.setattr(
        "app.services.sources.article.ArticleSourceAdapter.fetch",
        lambda _self, url: RawSource(
            requested_url=url,
            final_url=url,
            content_type="text/html",
            content=html,
        ),
    )
    response = client.post(
        "/api/v1/ingestion/links",
        json={"url": "https://example.com/agent-study", "provider": "mistral"},
    )

    assert run_pending_submissions(db) == 1
    submission = db.get(LinkSubmission, response.json()["id"])
    assert submission.status == "completed"
    assert submission.review_status == "needs_review"
    assert submission.title == "Production agent study"
    assert submission.classification["normalized_source"]["source_type"] == "article"
    assert "operational outcomes" in submission.extracted_markdown


def test_private_url_is_pending_without_fetching_in_request(client):
    response = client.post("/api/v1/ingestion/links", json={"url": "http://127.0.0.1/admin"})
    assert response.status_code == 202
    assert response.json()["status"] == "pending"


def test_invalid_private_url_fails_with_typed_error_and_can_retry(client, db):
    response = client.post("/api/v1/ingestion/links", json={"url": "http://127.0.0.1/admin"})
    submission_id = response.json()["id"]

    assert run_pending_submissions(db) == 1
    submission = client.get("/api/v1/ingestion/links").json()[0]
    assert submission["status"] == "failed"
    assert submission["stage"] == "failed"
    assert submission["error_code"] == "INVALID_URL"
    assert submission["error"] == "URL không hợp lệ hoặc không thể truy cập công khai."

    retried = client.post(f"/api/v1/ingestion/links/{submission_id}/retry")
    assert retried.status_code == 200
    assert retried.json()["status"] == "pending"
    assert retried.json()["attempt_count"] == 0


def test_retry_validates_override_and_replaces_removed_legacy_provider(client, db):
    response = client.post(
        "/api/v1/ingestion/links",
        json={"url": "http://127.0.0.1/legacy-provider", "provider": "deepseek"},
    )
    assert run_pending_submissions(db) == 1
    item = db.get(LinkSubmission, response.json()["id"])
    item.provider_name = "mock"
    db.commit()

    invalid = client.post(f"/api/v1/ingestion/links/{item.id}/retry?provider=unknown")
    assert invalid.status_code == 422

    retried = client.post(f"/api/v1/ingestion/links/{item.id}/retry")
    assert retried.status_code == 200
    assert retried.json()["provider_name"] == "mistral"


def test_resubmitting_failed_url_requeues_with_selected_provider(client, db):
    url = "http://127.0.0.1/resubmit"
    original = client.post("/api/v1/ingestion/links", json={"url": url, "provider": "openrouter"})
    assert run_pending_submissions(db) == 1
    failed = db.get(LinkSubmission, original.json()["id"])
    assert failed.status == "failed"

    resubmitted = client.post("/api/v1/ingestion/links", json={"url": url, "provider": "deepseek"})

    assert resubmitted.status_code == 202
    assert resubmitted.json()["id"] == original.json()["id"]
    assert resubmitted.json()["status"] == "pending"
    assert resubmitted.json()["provider_name"] == "deepseek"
    assert db.query(LinkSubmission).count() == 1


def test_timeout_rate_limit_auth_empty_parser_and_unsupported_errors(client, db, monkeypatch):
    cases = [
        SourceError("FETCH_TIMEOUT", "Timed out", retryable=False),
        SourceError("RATE_LIMITED", "Rate limited", retryable=False),
        SourceError("AUTH_REQUIRED", "Login required"),
        SourceError("EMPTY_CONTENT", "No content"),
        SourceError("UNSUPPORTED_CONTENT_TYPE", "Unsupported type"),
        SourceError("EXTRACTION_FAILED", "Parser failed"),
    ]
    for index, failure in enumerate(cases):
        monkeypatch.setattr(
            "app.services.ingestion.fetch_url",
            lambda _url, _on_stage, current=failure: (_ for _ in ()).throw(current),
        )
        response = client.post(
            "/api/v1/ingestion/links", json={"url": f"https://example.com/failure-{index}"}
        )
        assert run_pending_submissions(db, max_jobs=1) == 1
        submission = db.get(LinkSubmission, response.json()["id"])
        assert submission.status == "failed"
        assert submission.error_code == failure.code


class UnmappedFailure(Exception):
    """Stands in for a defect the intake pipeline has no specific mapping for."""


def test_unexpected_failures_keep_a_diagnosable_but_non_leaking_error(client, db, monkeypatch):
    monkeypatch.setattr(
        "app.services.ingestion.fetch_url",
        lambda _url, _on_stage: (_ for _ in ()).throw(
            UnmappedFailure("secret-runtime-marker https://user:pass@internal/doc")
        ),
    )
    response = client.post("/api/v1/ingestion/links", json={"url": "https://example.com/unmapped"})

    assert run_pending_submissions(db, max_jobs=1) == 1
    submission = db.get(LinkSubmission, response.json()["id"])

    assert submission.status == "failed"
    assert submission.error_code == "INTERNAL_ERROR"
    # The type and stage locate the defect; the exception message never reaches the row.
    assert submission.error_details["exception_type"] == "UnmappedFailure"
    assert submission.error_details["stage"] == "normalizing"
    assert "secret-runtime-marker" not in json.dumps(submission.error_details)
    assert "secret-runtime-marker" not in (submission.error or "")


def test_connection_and_tls_failures_map_to_distinct_actionable_codes():
    connect = _source_error(httpx.ConnectError("dns lookup for secret-host failed"))
    tls = _source_error(ssl.SSLCertVerificationError("certificate verify failed"))
    database = _source_error(SQLAlchemyError("relation link_submission does not exist"))

    assert (connect.code, connect.retryable) == ("DNS_FAILED", True)
    assert (tls.code, tls.retryable) == ("TLS_FAILED", False)
    assert (database.code, database.retryable) == ("DATABASE_ERROR", True)
    assert "secret-host" not in connect.message


def test_actionable_source_limitations_are_separated_from_defects():
    assert SourceError("ACCESS_DENIED", "Denied").user_actionable is True
    assert SourceError("TRANSCRIPT_SOURCE_INVALID", "Invalid").user_actionable is True
    assert SourceError("INTERNAL_ERROR", "Broken").user_actionable is False
    assert SourceError("DATABASE_ERROR", "Broken").user_actionable is False


def test_ai_provider_failures_are_typed_without_leaking_response_details():
    request = httpx.Request("POST", "https://provider.example/chat/completions")
    rate_limited = httpx.Response(429, request=request, text="sensitive provider detail")
    server_error = httpx.Response(503, request=request, text="upstream stack trace")

    rate_error = _source_error(
        httpx.HTTPStatusError("rate limited", request=request, response=rate_limited),
        "analyzing",
    )
    unavailable = _source_error(
        httpx.HTTPStatusError("unavailable", request=request, response=server_error),
        "analyzing",
    )

    assert rate_error.code == "AI_PROVIDER_RATE_LIMITED"
    assert rate_error.retryable is True
    assert unavailable.code == "AI_PROVIDER_UNAVAILABLE"
    assert unavailable.retryable is True
    assert "sensitive" not in rate_error.message
    assert "stack trace" not in unavailable.message


def test_transient_failure_retries_then_succeeds(client, db, monkeypatch):
    attempts = 0
    content = "Reliable business agent research content with enough detail. " * 3

    def flaky_fetch(_url: str, _on_stage) -> FetchedSourceResult:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("temporary network failure")
        return result("https://example.com/retry", "Retry succeeds", content)

    monkeypatch.setattr("app.services.ingestion.fetch_url", flaky_fetch)
    monkeypatch.setattr("app.services.ingestion.settings.intake_retry_base_seconds", 0)
    response = client.post(
        "/api/v1/ingestion/links",
        json={"url": "https://example.com/retry", "provider": "mistral"},
    )

    assert run_pending_submissions(db, max_jobs=1) == 1
    first = db.get(LinkSubmission, response.json()["id"])
    assert first.status == "pending"
    assert first.stage == "retry_scheduled"
    assert first.attempt_count == 1

    assert run_pending_submissions(db, max_jobs=1) == 1
    db.refresh(first)
    assert first.status == "completed"
    assert first.attempt_count == 2


def test_partial_success_is_reviewable_and_does_not_crash_worker(client, db, monkeypatch):
    monkeypatch.setattr(
        "app.services.ingestion.fetch_url",
        lambda _url, _on_stage: result(
            "https://example.com/metadata-only",
            "Metadata only source",
            "Short metadata",
            partial=True,
        ),
    )
    response = client.post(
        "/api/v1/ingestion/links", json={"url": "https://example.com/metadata-only"}
    )

    assert run_pending_submissions(db) == 1
    submission = db.get(LinkSubmission, response.json()["id"])
    assert submission.status == "partial_success"
    assert submission.review_status == "needs_review"
    assert submission.classification["normalized_source"]["limitation_code"] == "METADATA_ONLY"


def test_user_supplied_reel_transcript_requeues_without_api_or_audit_leakage(
    client, db, monkeypatch
):
    marker = "private transcript marker with grounded human review evidence " * 3

    def facebook_result(_url, _on_stage):
        return FetchedSourceResult(
            NormalizedSource(
                id="facebook:reel-test",
                source_type="facebook",
                canonical_url="https://www.facebook.com/reel/123",
                title="Public Reel",
                description="Public Reel metadata.",
                raw_text="Public Reel metadata.",
                metadata={"resource_kind": "reel", "metadata_only": True},
                collection_status="PARTIAL",
                limitation_code="TRANSCRIPT_UNAVAILABLE",
                limitation_message="A transcript is unavailable.",
            )
        )

    monkeypatch.setattr("app.services.ingestion.fetch_url", facebook_result)
    created = client.post(
        "/api/v1/ingestion/links",
        json={"url": "https://www.facebook.com/reel/123", "provider": "mistral"},
    ).json()
    response = client.put(
        f"/api/v1/ingestion/links/{created['id']}/transcript",
        json={
            "language": "en",
            "segments": [
                {"timestamp_seconds": 12, "text": marker},
                {"timestamp_seconds": 62, "text": "Owner review remains required."},
            ],
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "pending"
    assert response.json()["transcript"] == {
        "configured": True,
        "language": "en",
        "segment_count": 2,
        "updated_at": response.json()["transcript"]["updated_at"],
    }
    assert marker not in response.text
    audit = db.query(AuditEvent).filter_by(action="link.transcript.upserted").one()
    assert audit.payload == {"language": "en", "segment_count": 2}
    assert marker not in str(audit.payload)

    assert run_pending_submissions(db) == 1
    item = db.get(LinkSubmission, created["id"])
    assert item.status == "completed"
    assert marker.strip() in item.extracted_markdown
    normalized = item.classification["normalized_source"]
    assert normalized["metadata"]["transcript_source"] == "user_supplied"
    assert normalized["limitation_code"] is None
    assert marker not in client.get("/api/v1/ingestion/links").text

    approved = client.post(f"/api/v1/ingestion/links/{item.id}/approve", json={})
    assert approved.status_code == 200
    blocked = client.put(
        f"/api/v1/ingestion/links/{item.id}/transcript",
        json={"language": "en", "segments": [{"timestamp_seconds": 1, "text": "replace"}]},
    )
    assert blocked.status_code == 409


def test_transcript_rejects_wrong_source_and_unordered_segments(client):
    article = client.post(
        "/api/v1/ingestion/links", json={"url": "https://example.com/article"}
    ).json()
    wrong_source = client.put(
        f"/api/v1/ingestion/links/{article['id']}/transcript",
        json={"language": "en", "segments": [{"timestamp_seconds": 1, "text": "text"}]},
    )
    reel = client.post(
        "/api/v1/ingestion/links", json={"url": "https://www.facebook.com/reel/456"}
    ).json()
    unordered = client.put(
        f"/api/v1/ingestion/links/{reel['id']}/transcript",
        json={
            "language": "en",
            "segments": [
                {"timestamp_seconds": 10, "text": "later"},
                {"timestamp_seconds": 1, "text": "earlier"},
            ],
        },
    )

    assert wrong_source.status_code == 422
    assert unordered.status_code == 422


def test_two_urls_redirecting_to_one_page_record_a_duplicate_instead_of_crashing(
    client, db, monkeypatch
):
    """The canonical URL is unique, so a second submission cannot claim it.

    Two different addresses reaching the same page is ordinary on the web: a shortener, a
    tracking wrapper, an http/https pair. Adopting the shared canonical URL for both rows
    violates the unique index and turns a routine duplicate into a database error the
    worker retries until the attempt budget runs out.
    """

    canonical = "https://publisher.example/canonical-report"
    monkeypatch.setattr(
        "app.services.ingestion.fetch_url",
        lambda _url, _on_stage=None: result(
            canonical,
            "Canonical report",
            "A grounded report body with enough text to be classified properly.",
        ),
    )
    first = client.post("/api/v1/ingestion/links", json={"url": canonical})
    assert run_pending_submissions(db, max_jobs=1) == 1

    second = client.post("/api/v1/ingestion/links", json={"url": "https://shortener.example/abc"})
    assert run_pending_submissions(db, max_jobs=1) == 1

    original = db.get(LinkSubmission, first.json()["id"])
    follower = db.get(LinkSubmission, second.json()["id"])

    assert follower.status == "completed"
    assert follower.review_status == "duplicate"
    assert follower.duplicate_of_id == original.id
    assert follower.error_code is None
    # The submitted address is kept, because the canonical one already belongs to the
    # original row and is what a reviewer needs to tell the two apart.
    assert follower.url == "https://shortener.example/abc"
    assert original.url == canonical
