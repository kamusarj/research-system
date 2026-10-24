import json
from pathlib import Path

import pytest

from app.schemas.paper_fit import PaperFitAssessment, PaperFitDimensions, PaperFitHardGates
from app.services.paper_fit import evaluate_paper_fit, route_fit_score, score_paper_fit

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "paper_fit_gold_v1.json"


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0, "not_relevant"),
        (39.99, "not_relevant"),
        (40, "watch"),
        (59.99, "watch"),
        (60, "draft_graph"),
        (79.99, "draft_graph"),
        (80, "priority_review"),
        (100, "priority_review"),
    ],
)
def test_decision_boundaries(score, expected):
    assert route_fit_score(score) == expected


def test_weighted_score_is_calculated_server_side():
    dimensions = PaperFitDimensions(
        system_fit=92,
        business_applicability=85,
        evidence_quality=78,
        novelty=74,
        implementation_value=90,
        gap_coverage=80,
        freshness=88,
    )
    assert score_paper_fit(dimensions) == 84.2


def test_failed_hard_gate_has_no_misleading_fit_score():
    result = evaluate_paper_fit(
        PaperFitAssessment(
            hard_gates=PaperFitHardGates(readable_content=False),
            dimensions=PaperFitDimensions(
                system_fit=100,
                business_applicability=100,
                evidence_quality=100,
                novelty=100,
                implementation_value=100,
                gap_coverage=100,
                freshness=100,
            ),
        )
    )
    assert result.fit_score is None
    assert result.decision == "hard_gate_failed"
    assert result.failed_gates == ["readable_content"]


def test_versioned_gold_fixture_routes_deterministically():
    fixtures = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    categories = [fixture["category"] for fixture in fixtures]
    assert len(fixtures) == 30
    assert len({fixture["id"] for fixture in fixtures}) == 30
    assert categories.count("core") == 10
    assert categories.count("enabling") == 10
    assert categories.count("tangential") == 5
    assert categories.count("irrelevant") == 5

    correct = 0
    for fixture in fixtures:
        result = evaluate_paper_fit(
            PaperFitAssessment(
                dimensions=PaperFitDimensions.model_validate(fixture["dimensions"]),
                matched_pillars=(
                    [fixture["expected_pillar"]] if fixture["expected_pillar"] else []
                ),
                confidence=0.9,
            )
        )
        correct += result.decision == fixture["expected_decision"]
    assert correct / len(fixtures) == 1
