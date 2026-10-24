"""Eval cho pipeline nghiên cứu sâu: chạy bộ câu hỏi mẫu theo biến thể rồi so sánh số đo.

Số đo đều tính tất định từ dữ liệu lượt chạy (thời gian, lượt gọi AI, token, độ phủ trích dẫn,
tỉ lệ trích dẫn khớp nguồn, tỉ lệ nguồn trùng, độ phủ góc nhìn, số tên miền); chỉ việc tạo ra
lượt chạy mới cần mô hình và máy tìm kiếm thật.
"""

import json
import time
from collections.abc import Callable
from pathlib import Path
from statistics import mean
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ResearchItem, ResearchRun, ResearchRunSource
from app.services.research_agent import runner
from app.services.research_agent.schemas import PERSPECTIVES
from app.services.research_agent.search import content_fingerprint, near_duplicate, simhash

DEFAULT_QUESTIONS = Path(__file__).with_name("research_eval_v1.json")
TERMINAL = {"completed", "failed", "cancelled"}


def load_questions(
    path: Path = DEFAULT_QUESTIONS, only: set[str] | None = None
) -> list[dict[str, Any]]:
    questions = json.loads(path.read_text(encoding="utf-8"))["questions"]
    return [q for q in questions if not only or q["id"] in only]


def run_question(
    db: Session,
    question: dict[str, Any],
    variant: str,
    *,
    advance: Callable[[Session, ResearchRun], ResearchRun] = runner.advance_research_run,
    max_steps: int = 40,
) -> dict[str, Any]:
    run = runner.create_run(db, question["question"], variant=variant, enforce_limits=False)
    started = time.monotonic()
    for _ in range(max_steps):
        db.refresh(run)
        if run.status in TERMINAL:
            break
        run.status = "running"
        db.commit()
        run = advance(db, run)
    db.refresh(run)
    return score_run(db, run, question, elapsed_seconds=time.monotonic() - started)


def score_run(
    db: Session, run: ResearchRun, question: dict[str, Any], *, elapsed_seconds: float
) -> dict[str, Any]:
    metrics = run.metrics_json or {}
    cited = int(metrics.get("cited_sentences", 0))
    uncited = int(metrics.get("uncited_sentences", 0))
    proposed = int(metrics.get("claims_proposed", 0))
    matched = int(metrics.get("claims_matched", 0))
    hits = int(metrics.get("hits_total", 0))
    report = db.get(ResearchItem, run.report_research_id) if run.report_research_id else None
    text = (report.content if report else "").casefold()
    entities = question.get("key_entities") or []
    cited_sources = [
        source
        for source in db.query(ResearchRunSource).filter_by(run_id=run.id)
        if source.citation_index is not None
    ]
    return {
        "id": question["id"],
        "run_id": run.id,
        "variant": run.variant,
        "status": run.status,
        "error_code": run.error_code,
        "wall_time_s": round(elapsed_seconds, 1),
        "llm_calls": int(metrics.get("llm_calls", 0)),
        "llm_cache_hits": int(metrics.get("llm_cache_hits", 0)),
        "input_tokens": int(metrics.get("input_tokens", 0)),
        "output_tokens": int(metrics.get("output_tokens", 0)),
        "total_tokens": int(metrics.get("total_tokens", 0))
        or int(metrics.get("input_tokens", 0)) + int(metrics.get("output_tokens", 0)),
        "prompt_chars": int(metrics.get("prompt_chars", 0)),
        "citation_coverage": round(cited / (cited + uncited), 3) if cited + uncited else 0.0,
        "cited_sentences": cited,
        "quote_verification_rate": round(matched / proposed, 3) if proposed else 0.0,
        "claims_verified": int(metrics.get("claims_verified", 0)),
        "duplicates_removed_rate": round(int(metrics.get("duplicates_removed", 0)) / hits, 3)
        if hits
        else 0.0,
        "cited_duplicate_rate": cited_duplicate_rate(cited_sources),
        "sources_cited": int(metrics.get("sources_cited", 0)),
        "unique_domains": int(metrics.get("unique_domains", 0)),
        "perspective_coverage": round(
            len(set(metrics.get("perspectives_covered") or []) & set(PERSPECTIVES))
            / len(PERSPECTIVES),
            3,
        ),
        "entity_recall": round(
            sum(1 for entity in entities if entity.casefold() in text) / len(entities), 3
        )
        if entities
        else 0.0,
    }


def cited_duplicate_rate(sources: list[ResearchRunSource]) -> float:
    """Tỉ lệ nguồn được trích dẫn là bản sao (y hệt hoặc gần giống) của một nguồn trích dẫn khác.

    Tính lại từ văn bản để so được cả biến thể không bật khử trùng."""
    seen: list[tuple[str, str]] = []
    duplicates = 0
    for source in sorted(sources, key=lambda item: item.citation_index or 0):
        fingerprint, sketch = content_fingerprint(source.content_text), simhash(source.content_text)
        if any(
            fingerprint == other or near_duplicate(sketch, other_sketch)
            for other, other_sketch in seen
        ):
            duplicates += 1
        seen.append((fingerprint, sketch))
    return round(duplicates / len(sources), 3) if sources else 0.0


SUMMARY_FIELDS = (
    "wall_time_s",
    "llm_calls",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "prompt_chars",
    "citation_coverage",
    "quote_verification_rate",
    "cited_duplicate_rate",
    "sources_cited",
    "unique_domains",
    "perspective_coverage",
    "entity_recall",
)


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [r for r in results if r["status"] == "completed"]
    summary: dict[str, Any] = {
        "runs": len(results),
        "completed": len(completed),
        "completion_rate": round(len(completed) / len(results), 3) if results else 0.0,
    }
    for field in SUMMARY_FIELDS:
        values = [r[field] for r in completed]
        summary[field] = round(mean(values), 3) if values else None
    return summary


def compare_markdown(baseline: dict[str, Any], candidate: dict[str, Any]) -> str:
    lines = [
        f"| Chỉ số | {baseline['variant']} | {candidate['variant']} | Thay đổi |",
        "|---|---|---|---|",
    ]
    for field in ("completion_rate", *SUMMARY_FIELDS):
        before = baseline["summary"].get(field)
        after = candidate["summary"].get(field)
        change = ""
        if isinstance(before, int | float) and isinstance(after, int | float) and before:
            change = f"{(after - before) / before:+.0%}"
        lines.append(f"| {field} | {before} | {after} | {change} |")
    return "\n".join(lines)


def run_eval(
    db: Session,
    *,
    variant: str,
    only: set[str] | None = None,
    questions_path: Path = DEFAULT_QUESTIONS,
) -> dict[str, Any]:
    # Lệnh vận hành chạy được kể cả khi tính năng chưa bật cho người dùng.
    settings.research_agent_enabled = True
    results = [
        run_question(db, question, variant) for question in load_questions(questions_path, only)
    ]
    return {"variant": variant, "results": results, "summary": summarize(results)}
