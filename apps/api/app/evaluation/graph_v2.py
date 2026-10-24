import argparse
import json
from itertools import combinations
from pathlib import Path
from typing import Any

from app.schemas.paper_fit import PaperFitAssessment, PaperFitDimensions
from app.services.paper_duplicates import near_duplicate_score
from app.services.paper_fit import evaluate_paper_fit
from app.services.placement import rank_pillar_placements

DEFAULT_FIXTURE = Path(__file__).resolve().parents[2] / "tests/fixtures/paper_fit_gold_v1.json"
ROUTING_PRECISION_TARGET = 0.85
PLACEMENT_RECALL_TARGET = 0.85
DUPLICATE_RECALL_TARGET = 0.90


def evaluate_gold_set(fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    schema_failures = 0
    routing_predictions: list[tuple[bool, bool]] = []
    placement_hits = 0
    placement_total = 0
    placement_details: list[dict[str, Any]] = []
    for fixture in fixtures:
        try:
            result = evaluate_paper_fit(
                PaperFitAssessment(
                    dimensions=PaperFitDimensions.model_validate(fixture["dimensions"]),
                    confidence=0.9,
                )
            )
        except (KeyError, TypeError, ValueError):
            schema_failures += 1
            continue
        expected_positive = fixture["expected_decision"] in {
            "draft_graph",
            "priority_review",
        }
        predicted_positive = result.decision in {"draft_graph", "priority_review"}
        routing_predictions.append((predicted_positive, expected_positive))
        expected_pillar = fixture.get("expected_pillar")
        if expected_pillar:
            candidates = [
                label for label, _score in rank_pillar_placements(fixture["title"], limit=3)
            ]
            hit = expected_pillar in candidates
            placement_total += 1
            placement_hits += int(hit)
            placement_details.append(
                {
                    "id": fixture["id"],
                    "expected": expected_pillar,
                    "top_three": candidates,
                    "hit": hit,
                }
            )

    predicted_positives = sum(predicted for predicted, _expected in routing_predictions)
    true_positives = sum(
        predicted and expected for predicted, expected in routing_predictions
    )
    routing_precision = true_positives / predicted_positives if predicted_positives else 0

    expected_duplicate_pairs = 0
    detected_duplicate_pairs = 0
    false_duplicate_pairs = 0
    duplicate_details: list[dict[str, Any]] = []
    for left, right in combinations(fixtures, 2):
        expected = bool(
            left.get("duplicate_group")
            and left.get("duplicate_group") == right.get("duplicate_group")
        )
        score = near_duplicate_score(
            left["title"],
            left["dimensions"],
            right["title"],
            right["dimensions"],
        )
        detected = score >= 0.80
        expected_duplicate_pairs += int(expected)
        detected_duplicate_pairs += int(expected and detected)
        false_duplicate_pairs += int(not expected and detected)
        if expected or detected:
            duplicate_details.append(
                {
                    "left": left["id"],
                    "right": right["id"],
                    "score": score,
                    "expected": expected,
                    "detected": detected,
                }
            )
    duplicate_recall = (
        detected_duplicate_pairs / expected_duplicate_pairs
        if expected_duplicate_pairs
        else 1.0
    )
    duplicate_precision = (
        detected_duplicate_pairs / (detected_duplicate_pairs + false_duplicate_pairs)
        if detected_duplicate_pairs + false_duplicate_pairs
        else 1.0
    )
    placement_recall = placement_hits / placement_total if placement_total else 0
    schema_failure_rate = schema_failures / len(fixtures) if fixtures else 0
    metrics = {
        "fixture_version": "paper-fit-gold-v1",
        "fixture_count": len(fixtures),
        "routing_precision": round(routing_precision, 4),
        "top_three_placement_recall": round(placement_recall, 4),
        "duplicate_recall": round(duplicate_recall, 4),
        "duplicate_precision": round(duplicate_precision, 4),
        "fixture_schema_failure_rate": round(schema_failure_rate, 4),
        "thresholds": {
            "routing_precision": ROUTING_PRECISION_TARGET,
            "top_three_placement_recall": PLACEMENT_RECALL_TARGET,
            "duplicate_recall": DUPLICATE_RECALL_TARGET,
            "fixture_schema_failure_rate_below": 0.01,
        },
    }
    passed = (
        routing_precision >= ROUTING_PRECISION_TARGET
        and placement_recall >= PLACEMENT_RECALL_TARGET
        and duplicate_recall >= DUPLICATE_RECALL_TARGET
        and schema_failure_rate < 0.01
    )
    return {
        "passed": passed,
        "metrics": metrics,
        "placement_details": placement_details,
        "duplicate_details": duplicate_details,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Graph Intelligence v2 gold fixtures")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()
    fixtures = json.loads(args.fixture.read_text(encoding="utf-8"))
    report = evaluate_gold_set(fixtures)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
