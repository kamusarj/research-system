import json
from pathlib import Path

from app.core.config import settings
from app.core.runtime_controls import rate_limiter
from app.evaluation.graph_v2 import evaluate_gold_set
from app.models import KnowledgeNode
from app.services.graph_invariants import check_graph_invariants
from app.services.ontology import ensure_seed_ontology
from app.services.paper_duplicates import near_duplicate_score
from app.services.placement import resolve_matched_pillars

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "paper_fit_gold_v1.json"


def test_graph_v2_gold_release_metrics_pass():
    report = evaluate_gold_set(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))

    assert report["passed"] is True
    assert report["metrics"]["routing_precision"] >= 0.85
    assert report["metrics"]["top_three_placement_recall"] >= 0.85
    assert report["metrics"]["duplicate_recall"] >= 0.90
    assert report["metrics"]["fixture_schema_failure_rate"] < 0.01


def test_deterministic_placement_sanitizes_provider_labels_and_adds_fallback():
    pillars = [
        "Agent System Architecture",
        "Evaluation, Risk & Governance",
        "Data, Knowledge & Memory",
    ]
    resolved = resolve_matched_pillars(
        "Human Approval Controls for Agent Actions",
        "The system uses auditable risk controls.",
        ["invented pillar", "evaluation, risk & governance"],
        pillars,
    )

    assert resolved == ["Evaluation, Risk & Governance"]


def test_near_duplicate_detector_catches_fixture_pair():
    fixtures = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    left, right = [
        item
        for item in fixtures
        if item.get("duplicate_group") == "knowledge-graph-technical-documents"
    ]

    assert (
        near_duplicate_score(
            left["title"], left["dimensions"], right["title"], right["dimensions"]
        )
        >= 0.80
    )


def test_readiness_reports_valid_seed_graph(client, db):
    ensure_seed_ontology(db)

    response = client.get("/api/v1/system/readiness")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["graph"]["valid"] is True
    assert response.json()["features"]["graph_v2"] is True
    assert "X-Process-Time-Ms" in response.headers


def test_graph_invariant_check_detects_hierarchy_cycle(db):
    ensure_seed_ontology(db)
    left = KnowledgeNode(
        node_type="Concept",
        canonical_label="Cycle left",
        normalized_key="cycle-left",
        lifecycle_status="approved",
    )
    right = KnowledgeNode(
        node_type="Concept",
        canonical_label="Cycle right",
        normalized_key="cycle-right",
        lifecycle_status="approved",
    )
    db.add_all([left, right])
    db.flush()
    left.primary_parent_id = right.id
    right.primary_parent_id = left.id
    db.commit()

    report = check_graph_invariants(db)

    assert report.valid is False
    assert any("cycle" in error.casefold() for error in report.errors)


def test_feature_flag_is_enforced_server_side(client, monkeypatch):
    monkeypatch.setattr(settings, "graph_v2_chat_enabled", False)

    response = client.get("/api/v1/chat/sessions")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "FEATURE_DISABLED"


def test_mutating_operation_rate_limit_is_typed(client, monkeypatch):
    rate_limiter.clear()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_apply_per_window", 1)
    monkeypatch.setattr(settings, "rate_limit_window_seconds", 60)

    first = client.post("/api/v1/graph/change-sets/missing/apply")
    second = client.post("/api/v1/graph/change-sets/missing/apply")

    assert first.status_code == 404
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "RATE_LIMITED"
    assert second.headers["Retry-After"]
    assert second.headers["X-RateLimit-Remaining"] == "0"
    rate_limiter.clear()
