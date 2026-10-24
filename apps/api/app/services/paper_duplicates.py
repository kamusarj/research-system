import difflib
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DocumentGraphWorkspace, PaperEvaluation, ResearchItem
from app.schemas.paper_fit import PaperFitDimensions


def _normalized_title(value: str) -> str:
    tokens = re.sub(r"[^a-z0-9]+", " ", value.casefold()).split()
    aliases = {
        "building": "construction",
        "graphs": "graph",
        "documentation": "document",
        "documents": "document",
    }
    normalized = [
        aliases.get(token, token[:-1] if token.endswith("s") else token)
        for token in tokens
    ]
    return " ".join(sorted(normalized))


def near_duplicate_score(
    left_title: str,
    left_dimensions: dict[str, Any],
    right_title: str,
    right_dimensions: dict[str, Any],
) -> float:
    title_score = difflib.SequenceMatcher(
        None, _normalized_title(left_title), _normalized_title(right_title)
    ).ratio()
    dimension_names = PaperFitDimensions.model_fields
    dimension_similarity = 1 - sum(
        abs(float(left_dimensions[name]) - float(right_dimensions[name])) / 100
        for name in dimension_names
    ) / len(dimension_names)
    return round(title_score * 0.75 + dimension_similarity * 0.25, 4)


def find_near_duplicate_workspaces(
    db: Session,
    workspace_id: str,
    title: str,
    dimensions: PaperFitDimensions,
    *,
    threshold: float = 0.80,
    limit: int = 5,
) -> list[tuple[str, float]]:
    candidates = list(
        db.execute(
            select(DocumentGraphWorkspace.id, ResearchItem.title, PaperEvaluation.dimension_scores)
            .join(ResearchItem, ResearchItem.id == DocumentGraphWorkspace.research_id)
            .join(PaperEvaluation, PaperEvaluation.workspace_id == DocumentGraphWorkspace.id)
            .where(DocumentGraphWorkspace.id != workspace_id)
            .limit(500)
        )
    )
    ranked = []
    current_dimensions = dimensions.model_dump()
    for candidate_id, candidate_title, candidate_dimensions in candidates:
        try:
            score = near_duplicate_score(
                title,
                current_dimensions,
                candidate_title,
                candidate_dimensions or {},
            )
        except (KeyError, TypeError, ValueError):
            continue
        if score >= threshold:
            ranked.append((candidate_id, score))
    return sorted(ranked, key=lambda item: (-item[1], item[0]))[:limit]
