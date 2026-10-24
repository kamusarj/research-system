from decimal import ROUND_HALF_UP, Decimal

from app.schemas.paper_fit import (
    PaperFitAssessment,
    PaperFitDecision,
    PaperFitDimensions,
    PaperFitResult,
)

RUBRIC_VERSION = "business-ai-agents-paper-fit-v1"
WEIGHTS = {
    "system_fit": Decimal("0.25"),
    "business_applicability": Decimal("0.20"),
    "evidence_quality": Decimal("0.15"),
    "novelty": Decimal("0.15"),
    "implementation_value": Decimal("0.10"),
    "gap_coverage": Decimal("0.10"),
    "freshness": Decimal("0.05"),
}


def score_paper_fit(dimensions: PaperFitDimensions) -> float:
    values = dimensions.model_dump()
    total = sum(Decimal(str(values[name])) * weight for name, weight in WEIGHTS.items())
    return float(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def route_fit_score(score: float) -> PaperFitDecision:
    if score < 40:
        return "not_relevant"
    if score < 60:
        return "watch"
    if score < 80:
        return "draft_graph"
    return "priority_review"


def evaluate_paper_fit(assessment: PaperFitAssessment) -> PaperFitResult:
    failed_gates = [
        name for name, passed in assessment.hard_gates.model_dump().items() if not passed
    ]
    score = None if failed_gates else score_paper_fit(assessment.dimensions)
    return PaperFitResult(
        rubric_version=RUBRIC_VERSION,
        fit_score=score,
        decision="hard_gate_failed" if failed_gates else route_fit_score(score or 0),
        failed_gates=failed_gates,
        dimensions=assessment.dimensions,
        matched_pillars=assessment.matched_pillars,
        candidate_parents=assessment.candidate_parents,
        contribution_types=assessment.contribution_types,
        overlaps_with=assessment.overlaps_with,
        fills_gaps=assessment.fills_gaps,
        limitations=assessment.limitations,
        reasoning_summary=assessment.reasoning_summary,
        confidence=assessment.confidence,
    )
