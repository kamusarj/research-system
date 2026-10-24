from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db import Base
from app.main import app
from app.models import (
    AuditEvent,
    DocumentGraphWorkspace,
    IntakeReceipt,
    IntakeReceiptItem,
    KnowledgeGap,
    LinkSubmission,
    ServiceAccount,
)
from app.schemas.intake_receipts import ReceiptCreate
from app.services.documents import get_object_storage
from app.services.intake_receipts import deliver_url_receipt
from app.services.object_storage import LocalObjectStorage


def receipt_payload(
    occurrence: str,
    *urls: str,
    namespace: str = "integration",
    container: str = "container-1",
):
    return {
        "source": {
            "type": "api",
            "namespace": namespace,
            "occurrence_ref": occurrence,
            "container_ref": container,
            "external_actor_ref": "external-actor-1",
            "metadata": {"schema_version": 1, "event_type": "api_request"},
        },
        "items": [{"kind": "url", "url": url, "provider": "mistral"} for url in urls],
    }


def use_storage(root: Path) -> LocalObjectStorage:
    storage = LocalObjectStorage(root, 20_000_000)
    app.dependency_overrides[get_object_storage] = lambda: storage
    return storage


def test_same_occurrence_and_url_replays_without_duplicate_job(client, db):
    marker_url = "https://example.com/receipt-replay?utm_source=secret-marker"
    marker_ref = "occurrence-secret-marker"
    payload = receipt_payload(marker_ref, marker_url)

    first = client.post("/api/v1/intake/receipts", json=payload)
    replay = client.post("/api/v1/intake/receipts", json=payload)

    assert first.status_code == 202, first.text
    assert replay.status_code == 200, replay.text
    assert first.json()["items"][0]["disposition"] == "queued"
    assert replay.json()["items"][0]["disposition"] == "replayed"
    assert replay.json()["replayed"] is True
    assert replay.json()["delivery_count"] == 2
    assert db.query(IntakeReceipt).count() == 1
    assert db.query(IntakeReceiptItem).count() == 1
    assert db.query(LinkSubmission).count() == 1

    audit_payloads = [
        event.payload
        for event in db.scalars(
            select(AuditEvent).where(AuditEvent.action == "intake.receipt.delivered")
        )
    ]
    assert len(audit_payloads) == 2
    assert marker_ref not in str(audit_payloads)
    assert marker_url not in str(audit_payloads)
    assert "secret-marker" not in str(audit_payloads)


def test_scoped_receipt_read_exposes_only_related_active_knowledge_gaps(client, db):
    receipt = client.post(
        "/api/v1/intake/receipts",
        json=receipt_payload("gap-event", "https://example.com/gap-source"),
    ).json()
    research = client.post(
        "/api/v1/research",
        json={
            "title": "Agent memory evidence",
            "type": "reference",
            "collection_method": "auto-collected",
            "content": "Evidence about durable agent memory.",
            "tags": ["Agent Memory"],
        },
    ).json()
    client.post(f"/api/v1/research/{research['id']}/submit-review")
    client.post(f"/api/v1/research/{research['id']}/approve")
    submission = db.query(LinkSubmission).one()
    submission.status = "completed"
    submission.stage = "completed"
    submission.review_status = "approved"
    submission.research_id = research["id"]
    db.add_all(
        [
            KnowledgeGap(
                key="low-coverage:agent-memory",
                title="Expand coverage for Agent Memory",
                concept_key="agent-memory",
                status="detected",
                coverage_count=1,
                reason="Agent Memory has one approved source.",
            ),
            KnowledgeGap(
                key="dismissed:agent-memory",
                title="Dismissed memory gap",
                concept_key="agent-memory",
                status="dismissed",
                coverage_count=1,
                reason="This alert was dismissed.",
            ),
            KnowledgeGap(
                key="low-coverage:unrelated",
                title="Unrelated gap",
                concept_key="unrelated",
                status="detected",
                coverage_count=1,
                reason="This belongs to another research item.",
            ),
        ]
    )
    db.commit()

    response = client.get(f"/api/v1/intake/receipts/{receipt['id']}")

    assert response.status_code == 200
    gaps = response.json()["items"][0]["knowledge_gaps"]
    assert [gap["concept_key"] for gap in gaps] == ["agent-memory"]
    assert gaps[0]["coverage_count"] == 1
    assert "another research item" not in response.text
    assert "dismissed" not in response.text.casefold()


def test_different_occurrences_preserve_provenance_and_share_url_job(client, db):
    url = "https://example.com/shared-research"

    first = client.post("/api/v1/intake/receipts", json=receipt_payload("event-1", url))
    second = client.post("/api/v1/intake/receipts", json=receipt_payload("event-2", url))

    assert first.status_code == 202
    assert second.status_code == 200
    assert second.json()["items"][0]["disposition"] == "linked_existing"
    assert first.json()["id"] != second.json()["id"]
    assert db.query(IntakeReceipt).count() == 2
    assert db.query(IntakeReceiptItem).count() == 2
    assert db.query(LinkSubmission).count() == 1
    assert len({item.link_submission_id for item in db.query(IntakeReceiptItem)}) == 1


def test_one_receipt_accepts_multiple_urls_and_append_only_edits(client, db):
    first_url = "https://example.com/first"
    second_url = "https://example.com/second"
    created = client.post("/api/v1/intake/receipts", json=receipt_payload("event-many", first_url))
    edited = client.post(
        "/api/v1/intake/receipts",
        json=receipt_payload("event-many", first_url, second_url),
    )
    omitted = client.post("/api/v1/intake/receipts", json=receipt_payload("event-many", second_url))

    assert created.status_code == 202
    assert edited.status_code == 202
    assert [item["disposition"] for item in edited.json()["items"]] == [
        "replayed",
        "queued",
    ]
    assert omitted.status_code == 200
    assert len(omitted.json()["items"]) == 2
    assert db.query(IntakeReceipt).count() == 1
    assert db.query(IntakeReceiptItem).count() == 2
    assert db.query(LinkSubmission).count() == 2


def test_occurrence_identity_conflict_is_typed_and_does_not_mutate_items(client, db):
    payload = receipt_payload("event-conflict", "https://example.com/original")
    assert client.post("/api/v1/intake/receipts", json=payload).status_code == 202
    conflicting = receipt_payload(
        "event-conflict", "https://example.com/other", container="different-container"
    )

    response = client.post("/api/v1/intake/receipts", json=conflicting)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SOURCE_OCCURRENCE_CONFLICT"
    assert db.query(IntakeReceiptItem).count() == 1
    assert db.query(LinkSubmission).count() == 1


def test_receipt_boundary_rejects_unknown_platform_payload_fields(client):
    payload = receipt_payload("unknown-field", "https://example.com/bounded")
    payload["source"]["message_content"] = "must-not-enter-the-boundary"

    response = client.post("/api/v1/intake/receipts", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
    assert "must-not-enter-the-boundary" not in response.text


def test_legacy_endpoint_dual_writes_each_occurrence_but_reuses_job(client, db):
    url = "https://example.com/legacy-compatible"

    first = client.post("/api/v1/ingestion/links", json={"url": url})
    repeated = client.post("/api/v1/ingestion/links", json={"url": url})

    assert first.status_code == 202
    assert repeated.status_code == 200
    assert first.json()["receipt_disposition"] == "queued"
    assert repeated.json()["receipt_disposition"] == "linked_existing"
    assert first.json()["receipt_id"] != repeated.json()["receipt_id"]
    assert db.query(LinkSubmission).count() == 1
    assert db.query(IntakeReceipt).count() == 2
    assert db.query(IntakeReceiptItem).count() == 2


def test_document_item_is_verified_before_ack_and_replays_without_orphans(client, db, tmp_path):
    use_storage(tmp_path)
    receipt = client.post("/api/v1/intake/receipts", json=receipt_payload("document-event")).json()
    content = b"%PDF-1.4\nDurable receipt document\n%%EOF"

    first = client.post(
        f"/api/v1/intake/receipts/{receipt['id']}/documents",
        data={"external_item_ref": "attachment-1", "provider": "mistral"},
        files={"file": ("paper.pdf", content, "application/pdf")},
    )
    replay = client.post(
        f"/api/v1/intake/receipts/{receipt['id']}/documents",
        data={"external_item_ref": "attachment-1", "provider": "mistral"},
        files={"file": ("paper.pdf", content, "application/pdf")},
    )

    assert first.status_code == 202, first.text
    assert replay.status_code == 200, replay.text
    assert first.json()["items"][0]["kind"] == "document"
    assert first.json()["items"][0]["disposition"] == "queued"
    assert replay.json()["items"][0]["disposition"] == "replayed"
    assert db.query(DocumentGraphWorkspace).count() == 1
    assert db.query(IntakeReceiptItem).count() == 1
    stored_files = [path for path in tmp_path.rglob("*") if path.is_file()]
    assert len(stored_files) == 1
    assert stored_files[0].read_bytes() == content


def test_document_ref_conflict_fails_and_same_bytes_in_new_occurrence_link_existing(
    client, db, tmp_path
):
    use_storage(tmp_path)
    first_receipt = client.post(
        "/api/v1/intake/receipts", json=receipt_payload("document-event-1")
    ).json()
    content = b"%PDF-1.4\nSame document bytes\n%%EOF"
    assert (
        client.post(
            f"/api/v1/intake/receipts/{first_receipt['id']}/documents",
            data={"external_item_ref": "attachment-1"},
            files={"file": ("paper.pdf", content, "application/pdf")},
        ).status_code
        == 202
    )

    conflict = client.post(
        f"/api/v1/intake/receipts/{first_receipt['id']}/documents",
        data={"external_item_ref": "attachment-1"},
        files={"file": ("paper.pdf", b"%PDF-1.4\nDifferent bytes\n%%EOF", "application/pdf")},
    )
    second_receipt = client.post(
        "/api/v1/intake/receipts", json=receipt_payload("document-event-2")
    ).json()
    linked = client.post(
        f"/api/v1/intake/receipts/{second_receipt['id']}/documents",
        data={"external_item_ref": "attachment-2"},
        files={"file": ("copy.pdf", content, "application/pdf")},
    )

    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "SOURCE_ITEM_CONFLICT"
    assert linked.status_code == 200
    assert linked.json()["items"][0]["disposition"] == "linked_existing"
    assert db.query(DocumentGraphWorkspace).count() == 1
    assert db.query(IntakeReceiptItem).count() == 2
    assert len([path for path in tmp_path.rglob("*") if path.is_file()]) == 1


def test_document_database_failure_removes_new_object(client, db, tmp_path, monkeypatch):
    use_storage(tmp_path)
    receipt = client.post(
        "/api/v1/intake/receipts", json=receipt_payload("document-failure")
    ).json()

    def fail_records(*_args, **_kwargs):
        raise RuntimeError("database-write-marker")

    monkeypatch.setattr("app.services.intake_receipts.add_document_records", fail_records)
    try:
        response = client.post(
            f"/api/v1/intake/receipts/{receipt['id']}/documents",
            data={"external_item_ref": "attachment-failure"},
            files={
                "file": (
                    "failure.pdf",
                    b"%PDF-1.4\nFailure cleanup\n%%EOF",
                    "application/pdf",
                )
            },
        )
    except RuntimeError as exc:
        assert str(exc) == "database-write-marker"
    else:
        assert response.status_code == 500

    assert db.query(DocumentGraphWorkspace).count() == 0
    assert db.query(IntakeReceiptItem).count() == 0
    assert [path for path in tmp_path.rglob("*") if path.is_file()] == []


def test_service_account_token_is_one_time_scoped_and_revocable(client, db):
    created = client.post(
        "/api/v1/auth/service-accounts",
        json={
            "name": "Intake adapter",
            "source_namespace": "adapter-one",
            "scopes": ["intake:submit", "intake:read-own"],
        },
    )
    assert created.status_code == 201, created.text
    token = created.json()["token"]
    account_id = created.json()["id"]
    account = db.get(ServiceAccount, account_id)
    assert account is not None
    assert account.token_hash != token
    assert len(account.token_hash) == 64
    listing = client.get("/api/v1/auth/service-accounts")
    assert listing.status_code == 200
    assert '"token":' not in listing.text

    headers = {"Authorization": f"Bearer {token}"}
    own = client.post(
        "/api/v1/intake/receipts",
        json=receipt_payload(
            "service-event", "https://example.com/service", namespace="adapter-one"
        ),
        headers=headers,
    )
    assert own.status_code == 202, own.text
    assert (
        client.get(f"/api/v1/intake/receipts/{own.json()['id']}", headers=headers).status_code
        == 200
    )

    wrong_namespace = client.post(
        "/api/v1/intake/receipts",
        json=receipt_payload(
            "wrong-namespace", "https://example.com/wrong", namespace="adapter-two"
        ),
        headers=headers,
    )
    forbidden_route = client.get("/api/v1/research", headers=headers)
    assert wrong_namespace.status_code == 403
    assert forbidden_route.status_code == 403

    revoked = client.delete(f"/api/v1/auth/service-accounts/{account_id}")
    assert revoked.status_code == 204
    assert (
        client.get(f"/api/v1/intake/receipts/{own.json()['id']}", headers=headers).status_code
        == 401
    )

    audit_text = str(
        [
            event.payload
            for event in db.scalars(
                select(AuditEvent).where(AuditEvent.entity_type == "service_account")
            )
        ]
    )
    assert token not in audit_text
    assert "adapter-one" not in audit_text


def test_service_account_cannot_read_another_namespace_receipt(client, db):
    created = client.post(
        "/api/v1/auth/service-accounts",
        json={"name": "Scoped adapter", "source_namespace": "scope-one"},
    ).json()
    other = client.post(
        "/api/v1/intake/receipts",
        json=receipt_payload("other-event", namespace="scope-two"),
    ).json()

    response = client.get(
        f"/api/v1/intake/receipts/{other['id']}",
        headers={"Authorization": f"Bearer {created['token']}"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCESS_DENIED"


def test_service_bearer_uses_scopes_without_browser_csrf(client, db, monkeypatch):
    read_only = client.post(
        "/api/v1/auth/service-accounts",
        json={
            "name": "Read-only adapter",
            "source_namespace": "read-only-scope",
            "scopes": ["intake:read-own"],
        },
    ).json()
    submitter = client.post(
        "/api/v1/auth/service-accounts",
        json={
            "name": "Submit adapter",
            "source_namespace": "submit-scope",
            "scopes": ["intake:submit", "intake:read-own"],
        },
    ).json()
    monkeypatch.setattr(settings, "auth_mode", "local")
    client.cookies.clear()

    denied = client.post(
        "/api/v1/intake/receipts",
        json=receipt_payload(
            "read-only-event",
            "https://example.com/read-only",
            namespace="read-only-scope",
        ),
        headers={"Authorization": f"Bearer {read_only['token']}"},
    )
    accepted = client.post(
        "/api/v1/intake/receipts",
        json=receipt_payload(
            "submit-event",
            "https://example.com/submit",
            namespace="submit-scope",
        ),
        headers={"Authorization": f"Bearer {submitter['token']}"},
    )

    assert denied.status_code == 403
    assert accepted.status_code == 202
    assert (
        client.get(
            f"/api/v1/intake/receipts/{accepted.json()['id']}",
            headers={"Authorization": f"Bearer {submitter['token']}"},
        ).status_code
        == 200
    )


def test_concurrent_identical_delivery_converges_to_one_receipt_item_and_job(tmp_path):
    database_path = tmp_path / "concurrent-receipts.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    data = ReceiptCreate.model_validate(
        receipt_payload("concurrent-event", "https://example.com/concurrent")
    )

    def deliver():
        with factory() as session:
            result = deliver_url_receipt(session, data)
            return next(iter(result.dispositions.values()))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: deliver(), range(2)))

    with Session(engine) as db:
        assert db.query(IntakeReceipt).count() == 1
        assert db.query(IntakeReceiptItem).count() == 1
        assert db.query(LinkSubmission).count() == 1
    assert sorted(results) == ["queued", "replayed"]
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_a_gateway_can_find_its_own_receipt_by_the_reference_it_already_has(client, db):
    """A Discord user holds a message ID, not a receipt ID, so the lookup must accept it."""

    account = client.post(
        "/api/v1/auth/service-accounts",
        json={
            "name": "Discord gateway",
            "source_namespace": "discord",
            "scopes": ["intake:submit", "intake:read-own"],
        },
    ).json()
    headers = {"Authorization": f"Bearer {account['token']}"}
    created = client.post(
        "/api/v1/intake/receipts",
        json=receipt_payload("discord-message-77", "https://example.com/a", namespace="discord"),
        headers=headers,
    ).json()

    found = client.get(
        "/api/v1/intake/receipts",
        params={"occurrence_ref": "discord-message-77"},
        headers=headers,
    )

    assert found.status_code == 200
    assert found.json()["id"] == created["id"]


def test_the_occurrence_lookup_cannot_reach_another_namespace(client, db):
    client.post(
        "/api/v1/intake/receipts",
        json=receipt_payload("shared-ref", "https://example.com/other", namespace="scope-two"),
    )
    account = client.post(
        "/api/v1/auth/service-accounts",
        json={
            "name": "Confined gateway",
            "source_namespace": "scope-one",
            "scopes": ["intake:submit", "intake:read-own"],
        },
    ).json()

    response = client.get(
        "/api/v1/intake/receipts",
        params={"occurrence_ref": "shared-ref"},
        headers={"Authorization": f"Bearer {account['token']}"},
    )

    # Guessing another system's reference must not reveal its intake.
    assert response.status_code == 404


def test_an_unknown_reference_is_a_plain_not_found(client, db):
    response = client.get("/api/v1/intake/receipts", params={"occurrence_ref": "never-seen"})

    assert response.status_code == 404
