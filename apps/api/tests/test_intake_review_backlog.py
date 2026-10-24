"""Cover the review queue, duplicate recovery and projection staleness.

Before these behaviours existed, 24 of 27 collected sources sat in `needs_review` with no
count anywhere in the product, duplicates of an unapproved original were left with no
research record and no route back, and applying a change set silently left search and
graph projections answering from the previous state.
"""

from sqlalchemy import select

from app.models import GraphChangeSet, GraphMutation, KnowledgeNode, LinkSubmission
from app.schemas.ingestion import LinkReview
from app.services.graph_changes import apply_change_set, approve_change_set, validate_change_set
from app.services.ingestion import approve_submission, review_backlog
from app.services.ontology import ensure_seed_ontology
from app.services.projection_state import mark_projection_rebuilt, projection_status
from tests.test_link_to_hierarchy import CLASSIFICATION


def _submission(db, url: str, **overrides) -> LinkSubmission:
    fields = {
        "url": url,
        "source_type": "manual",
        "status": "completed",
        "stage": "completed",
        "review_status": "needs_review",
        "title": f"Report at {url}",
        "extracted_markdown": "A grounded report about retrieval augmented memory.",
        "classification": CLASSIFICATION,
        **overrides,
    }
    item = LinkSubmission(**fields)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def test_the_backlog_reports_what_is_waiting_on_a_person(client, db):
    ensure_seed_ontology(db)
    _submission(db, "https://publisher.example/a")
    _submission(db, "https://publisher.example/b")
    _submission(db, "https://publisher.example/c", review_status="rejected")

    backlog = client.get("/api/v1/ingestion/links/backlog").json()

    assert backlog["needs_review"] == 2
    assert backlog["rejected"] == 1
    # The threshold that decides automatic approval should not be a server-side secret.
    assert 0 < backlog["auto_approve_confidence"] <= 1


def test_bulk_approval_clears_the_queue_and_reports_each_outcome(client, db):
    ensure_seed_ontology(db)
    _submission(db, "https://publisher.example/a")
    _submission(db, "https://publisher.example/b")
    already = _submission(db, "https://publisher.example/c", review_status="rejected")

    response = client.post(
        "/api/v1/ingestion/links/bulk-review", json={"decision": "approve"}
    ).json()

    assert len(response["approved"]) == 2
    assert response["backlog"]["needs_review"] == 0
    # The rejected record was never in the queue, so it is untouched rather than revived.
    assert db.get(LinkSubmission, already.id).review_status == "rejected"


def test_bulk_review_keeps_going_when_one_item_cannot_be_decided(client, db):
    ensure_seed_ontology(db)
    good = _submission(db, "https://publisher.example/a")
    stale = _submission(db, "https://publisher.example/b", review_status="approved")

    response = client.post(
        "/api/v1/ingestion/links/bulk-review",
        json={"decision": "approve", "submission_ids": [stale.id, good.id]},
    ).json()

    assert response["approved"] == [good.id]
    assert response["skipped"][0]["id"] == stale.id
    assert "approved" in response["skipped"][0]["reason"]


def test_a_duplicate_of_an_unpublished_original_recovers_when_that_original_is_approved(
    client, db
):
    ensure_seed_ontology(db)
    original = _submission(db, "https://publisher.example/original")
    follower = _submission(
        db,
        "https://publisher.example/copy",
        review_status="duplicate",
        duplicate_of_id=original.id,
    )

    assert follower.research_id is None

    approve_submission(db, original, LinkReview())
    db.refresh(follower)

    # The copy was not lost: publishing the original is what gives it a research record.
    assert follower.research_id == original.research_id


def test_duplicates_awaiting_their_original_are_counted_separately(client, db):
    ensure_seed_ontology(db)
    original = _submission(db, "https://publisher.example/original")
    _submission(
        db,
        "https://publisher.example/copy",
        review_status="duplicate",
        duplicate_of_id=original.id,
    )

    assert review_backlog(db)["duplicates_awaiting_original"] == 1


def test_applying_a_change_set_marks_the_derived_projections_stale(client, db):
    ensure_seed_ontology(db)
    item = _submission(db, "https://publisher.example/agent-memory")
    approve_submission(db, item, LinkReview())
    change_set = db.scalar(select(GraphChangeSet).where(GraphChangeSet.origin_id == item.id))

    assert all(not status["stale"] for status in projection_status(db))

    validate_change_set(db, change_set)
    for mutation in db.scalars(
        select(GraphMutation).where(GraphMutation.change_set_id == change_set.id)
    ):
        mutation.review_decision = "accepted"
    db.commit()
    approve_change_set(db, change_set)
    apply_change_set(db, change_set)

    statuses = {status["target"]: status for status in projection_status(db)}

    assert db.scalar(select(KnowledgeNode).where(KnowledgeNode.canonical_label == "pgvector"))
    assert statuses["graph"]["stale"] is True
    assert statuses["search"]["stale"] is True


def test_rebuilding_a_projection_clears_only_its_own_staleness(client, db):
    ensure_seed_ontology(db)
    item = _submission(db, "https://publisher.example/agent-memory")
    approve_submission(db, item, LinkReview())
    change_set = db.scalar(select(GraphChangeSet).where(GraphChangeSet.origin_id == item.id))
    validate_change_set(db, change_set)
    for mutation in db.scalars(
        select(GraphMutation).where(GraphMutation.change_set_id == change_set.id)
    ):
        mutation.review_decision = "accepted"
    db.commit()
    approve_change_set(db, change_set)
    apply_change_set(db, change_set)

    mark_projection_rebuilt(db, target="graph")
    statuses = {status["target"]: status for status in projection_status(db)}

    assert statuses["graph"]["stale"] is False
    assert statuses["search"]["stale"] is True


def test_projection_status_is_readable_over_the_api(client, db):
    response = client.get("/api/v1/graph/projections")

    assert response.status_code == 200
    assert {status["target"] for status in response.json()} == {"graph", "search"}


def test_backlog_counts_are_whole_numbers_wherever_they_are_read(client, db):
    """A count rendered as "0.0 sources are waiting" is a bug, not a rounding detail."""

    ensure_seed_ontology(db)
    _submission(db, "https://publisher.example/a")

    from_endpoint = client.get("/api/v1/ingestion/links/backlog").json()
    from_bulk = client.post(
        "/api/v1/ingestion/links/bulk-review", json={"decision": "reject"}
    ).json()["backlog"]

    for payload in (from_endpoint, from_bulk):
        for field in ("needs_review", "approved", "rejected", "duplicate", "failed"):
            assert isinstance(payload[field], int), f"{field} should be a whole number"
        assert isinstance(payload["auto_approve_confidence"], float)


def test_an_unknown_status_filter_is_refused_rather_than_answered_with_nothing(client, db):
    """An empty list is indistinguishable from "no data", which hides a typo."""

    ensure_seed_ontology(db)
    _submission(db, "https://publisher.example/a")

    valid = client.get("/api/v1/ingestion/links", params={"status": "completed"})
    invalid = client.get("/api/v1/ingestion/links", params={"status": "complete"})

    assert valid.status_code == 200
    assert len(valid.json()) == 1
    assert invalid.status_code == 422


def test_an_unexpected_failure_on_one_item_does_not_discard_the_other_decisions(
    client, db, monkeypatch
):
    """The whole point of a batch endpoint is that it does not lose work on one bad row."""

    ensure_seed_ontology(db)
    broken = _submission(db, "https://publisher.example/broken")
    healthy = _submission(db, "https://publisher.example/healthy")
    real_approve = approve_submission

    def approve_unless_broken(session, item, review):
        if item.id == broken.id:
            raise RuntimeError("secret-runtime-marker")
        return real_approve(session, item, review)

    monkeypatch.setattr("app.api.ingestion.approve_submission", approve_unless_broken)

    response = client.post(
        "/api/v1/ingestion/links/bulk-review",
        json={"decision": "approve", "submission_ids": [broken.id, healthy.id]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] == [healthy.id]
    assert payload["skipped"][0]["id"] == broken.id
    # The reason names the failure type, never the exception message.
    assert payload["skipped"][0]["reason"] == "RuntimeError"
    assert "secret-runtime-marker" not in response.text
