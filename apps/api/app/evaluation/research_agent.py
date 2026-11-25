"""Eval cho pipeline nghiên cứu sâu: chạy bộ câu hỏi mẫu theo biến thể rồi so sánh số đo.

Số đo đều tính tất định từ dữ liệu lượt chạy (thời gian, lượt gọi AI, token, độ phủ trích dẫn,
tỉ lệ trích dẫn khớp nguồn, tỉ lệ nguồn trùng, độ phủ góc nhìn, số tên miền); chỉ việc tạo ra
lượt chạy mới cần mô hình và máy tìm kiếm thật.
"""

import hashlib
import ipaddress
import json
import math
import os
import re
import subprocess
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ResearchItem, ResearchRun, ResearchRunClaim, ResearchRunSource
from app.services.research_agent import runner
from app.services.research_agent.schemas import PERSPECTIVES
from app.services.research_agent.search import (
    SearchHit,
    content_fingerprint,
    content_terms,
    near_duplicate,
    simhash,
    text_relevance,
)

DEFAULT_QUESTIONS = Path(__file__).with_name("research_eval_v1.json")
TERMINAL = {"completed", "failed", "cancelled"}
MANIFEST_VERSION = "research-eval-v2"
QUALITY_GATES = {"citation_coverage": 1.0, "perspective_coverage": 1.0}
CORPUS_VERSION = "research-public-corpus-v1"
MAX_CORPUS_BYTES = 32_000_000
PROVIDER_STOP_CODES = frozenset(
    {
        "AI_PROVIDER_AUTH_FAILED",
        "AI_PROVIDER_ERROR",
        "AI_PROVIDER_RATE_LIMITED",
        "AI_PROVIDER_UNAVAILABLE",
    }
)
# Explicit allowlist: never export settings wholesale (it includes credentials).
EVAL_CONFIG_FIELDS = (
    "research_search_providers",
    "searxng_engines",
    "research_llm_concurrency",
    "research_fetch_concurrency",
    "research_max_queries",
    "research_hits_per_query",
    "research_max_sources",
    "research_max_per_domain",
    "research_source_chars",
    "research_extract_batch_chars",
    "research_max_claims_per_source",
    "research_max_llm_calls",
    "research_entailment_enabled",
    "research_max_attempts",
    "ai_max_output_tokens",
    "ai_request_timeout",
    "codex_effort",
    "claude_code_effort",
    "chatgpt_plan_reasoning_effort",
)


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
    cache_salt: str = "",
    max_steps: int = 40,
) -> dict[str, Any]:
    # Người tạo riêng: worker không nhận các lượt này, nên eval tự điều khiển và đo đúng thời gian.
    run = runner.create_run(
        db,
        question["question"],
        variant=variant,
        enforce_limits=False,
        actor=runner.EVAL_ACTOR,
        cache_salt=cache_salt,
    )
    started = time.monotonic()
    for _ in range(max_steps):
        db.refresh(run)
        if run.status in TERMINAL:
            break
        if run.next_attempt_at and run.status == "queued":
            wait = (_aware(run.next_attempt_at) - runner.utcnow()).total_seconds()
            if wait > 0:
                time.sleep(min(wait, 120))
        run = advance(db, runner.claim_run(db, run))
    db.refresh(run)
    return score_run(db, run, question, elapsed_seconds=time.monotonic() - started)


def _aware(value):
    return value if value.tzinfo else value.replace(tzinfo=runner.utcnow().tzinfo)


def report_body(markdown: str) -> str:
    """Phần nội dung báo cáo: bỏ phần đầu (có chép lại câu hỏi) và các mục Nguồn/Phương pháp."""
    body: list[str] = []
    skipping = False
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            skipping = stripped[3:] in ("Nguồn", "Phương pháp", "Khoảng trống bằng chứng")
            continue
        if not skipping and not stripped.startswith(("#", ">")):
            body.append(line)
    return "\n".join(body)


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
    text = report_body(report.content if report else "").casefold()
    entities = question.get("key_entities") or []
    cited_sources = [
        source
        for source in db.query(ResearchRunSource).filter_by(run_id=run.id)
        if source.citation_index is not None
    ]
    sources = list(db.query(ResearchRunSource).filter_by(run_id=run.id))
    source_material = sorted(
        (source.url, content_fingerprint(source.content_text))
        for source in sources
        if source.content_text
    )
    covered = set(metrics.get("perspectives_covered") or [])
    verified = set(
        db.scalars(
            select(ResearchRunClaim.perspective)
            .where(ResearchRunClaim.run_id == run.id, ResearchRunClaim.status == "verified")
            .distinct()
        )
    )
    covered_perspectives = [perspective for perspective in PERSPECTIVES if perspective in covered]
    return {
        "id": question["id"],
        "run_id": run.id,
        "variant": run.variant,
        "status": run.status,
        "error_code": run.error_code,
        "provider": run.provider_name,
        "model": run.model_name,
        "source_snapshot_sha256": _digest(source_material) if source_material else None,
        "wall_time_s": round(elapsed_seconds, 1),
        "llm_calls": int(metrics.get("llm_calls", 0)),
        "llm_cache_hits": int(metrics.get("llm_cache_hits", 0)),
        "usage_complete_calls": int(metrics.get("usage_complete_calls", 0)),
        "usage_missing_calls": int(metrics.get("usage_missing_calls", 0)),
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
        "perspective_coverage": round(len(covered_perspectives) / len(PERSPECTIVES), 3),
        "perspectives_covered": covered_perspectives,
        "perspectives_with_verified_claims": [p for p in PERSPECTIVES if p in verified],
        "writer_fallback_perspectives": metrics.get("writer_fallback_perspectives", []),
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
COST_TOTAL_FIELDS = {"llm_calls", "input_tokens", "output_tokens", "total_tokens", "prompt_chars"}


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [r for r in results if r["status"] == "completed"]
    summary: dict[str, Any] = {
        "runs": len(results),
        "completed": len(completed),
        "completion_rate": round(len(completed) / len(results), 3) if results else 0.0,
        "cost_basis": "all_attempted_runs",
        "usage_missing_calls": sum(r.get("usage_missing_calls", 0) for r in results),
    }
    for field in SUMMARY_FIELDS:
        # Costs include failed/cancelled runs. Quality is conditional on completion and labelled.
        population = results if field in COST_TOTAL_FIELDS or field == "wall_time_s" else completed
        values = [r[field] for r in population]
        summary[field] = (
            (sum(values) if field in COST_TOTAL_FIELDS else round(mean(values), 3))
            if values
            else None
        )
    return summary


def comparison_issues(baseline: dict[str, Any], candidate: dict[str, Any]) -> list[str]:
    """Fail closed for KPI claims; diagnostic tables remain available for legacy artifacts."""
    issues: list[str] = []
    if (baseline.get("variant"), candidate.get("variant")) != ("reference", "optimized"):
        issues.append("KPI yêu cầu biến thể reference trước và optimized sau.")
    before_rows, after_rows = baseline.get("results", []), candidate.get("results", [])
    before = {r["id"]: r for r in before_rows}
    after = {r["id"]: r for r in after_rows}
    if not before or before.keys() != after.keys():
        issues.append("Tập câu hỏi không trùng khớp đầy đủ.")
    if len(before) != len(before_rows) or len(after) != len(after_rows):
        issues.append("Có mã câu hỏi trùng lặp.")
    manifests = [baseline.get("manifest") or {}, candidate.get("manifest") or {}]
    if any(m.get("version") != MANIFEST_VERSION for m in manifests):
        issues.append("Thiếu manifest tái lập phiên bản hiện hành.")
    else:
        first, second = manifests
        required = {
            "questions_sha256",
            "selected_questions_sha256",
            "question_ids",
            "full_question_ids",
            "config",
            "code",
            "prompt_versions",
            "provider_models",
            "quality_gates",
            "corpus",
        }
        if any(not required.issubset(m) for m in manifests):
            issues.append("Manifest thiếu trường bắt buộc.")
        for field in (
            "questions_sha256",
            "selected_questions_sha256",
            "question_ids",
            "full_question_ids",
            "config",
            "code",
            "prompt_versions",
            "provider_models",
            "quality_gates",
            "corpus",
        ):
            if first.get(field) != second.get(field):
                issues.append(f"Manifest khác nhau: {field}.")
        if any(
            set(m.get("question_ids", [])) != set(rows)
            or set(m.get("full_question_ids", [])) != set(rows)
            for m, rows in zip(manifests, (before, after), strict=True)
        ):
            issues.append("Chưa đủ toàn bộ câu hỏi của bộ đánh giá đã khai báo.")
        if any(
            not m.get("provider_models") or not m.get("code", {}).get("source_sha256")
            for m in manifests
        ):
            issues.append("Thiếu danh tính provider/model hoặc fingerprint mã nguồn.")
        if any(m.get("cache_policy") != "cold-per-evaluation" for m in manifests):
            issues.append("Không xác nhận cache lạnh cho từng lượt đánh giá.")
        for manifest, variant in zip(manifests, ("reference", "optimized"), strict=True):
            flags = manifest.get("variant_flags")
            expected = runner.VARIANTS[variant]
            if not isinstance(flags, dict) or flags.keys() != expected.keys() or any(
                flags[key] is not value for key, value in expected.items()
            ):
                issues.append(f"Cờ pipeline không khớp biến thể {variant}.")
        for manifest in manifests:
            corpus = manifest.get("corpus")
            checksum = corpus.get("sha256") if isinstance(corpus, dict) else None
            if (
                not isinstance(corpus, dict)
                or corpus.get("mode") != "frozen"
                or not isinstance(checksum, str)
                or not re.fullmatch(r"[0-9a-f]{64}", checksum)
            ):
                issues.append("KPI yêu cầu corpus nguồn cố định có checksum.")
                break
        if any(not m.get("config", {}).get("research_entailment_enabled") for m in manifests):
            issues.append("Kiểm tra suy luận bị tắt trong cấu hình.")
    for qid in sorted(before.keys() & after.keys()):
        a, b = before[qid], after[qid]
        if not all(
            isinstance(row.get(field), str) and row[field].strip()
            for row in (a, b)
            for field in ("provider", "model")
        ) or (a.get("provider"), a.get("model")) != (b.get("provider"), b.get("model")):
            issues.append(f"{qid}: provider/model không trùng khớp hoặc bị thiếu.")
        if any(row.get("status") != "completed" for row in (a, b)):
            issues.append(f"{qid}: có lượt chưa hoàn tất; chi phí vẫn được tính.")
        if any(
            row.get("usage_missing_calls", 0)
            or row.get("usage_complete_calls", -1) != row.get("llm_calls", 0)
            for row in (a, b)
        ):
            issues.append(f"{qid}: thiếu usage của một hoặc nhiều lần gọi.")
        if not a.get("source_snapshot_sha256") or (
            a.get("source_snapshot_sha256") != b.get("source_snapshot_sha256")
        ):
            issues.append(f"{qid}: chưa chứng minh cùng bản chụp nguồn.")
        if any(
            not _finite_number(row.get(field)) or not minimum <= row[field] <= 1
            for row in (a, b)
            for field, minimum in QUALITY_GATES.items()
        ):
            issues.append(f"{qid}: chưa đạt cổng chất lượng trích dẫn/góc nhìn.")
        if any(
            not _finite_number(row.get("entity_recall")) or not 0 <= row["entity_recall"] <= 1
            for row in (a, b)
        ):
            issues.append(f"{qid}: số đo độ phủ thực thể không hợp lệ.")
        elif b["entity_recall"] < a["entity_recall"]:
            issues.append(f"{qid}: độ phủ thực thể giảm.")
    return issues


def _finite_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def compare_markdown(baseline: dict[str, Any], candidate: dict[str, Any]) -> str:
    """Show all attempted costs; report changes only for a fully comparable pair."""
    before = summarize(baseline.get("results", []))
    after = summarize(candidate.get("results", []))
    shared = {r["id"] for r in baseline.get("results", [])} & {
        r["id"] for r in candidate.get("results", [])
    }
    issues = comparison_issues(baseline, candidate)
    lines = [
        f"Câu hỏi so sánh: {len(shared)}; đã tính mọi lượt, kể cả thất bại.",
        "",
        "Đủ điều kiện so sánh KPI." if not issues else "Chưa đủ điều kiện kết luận KPI.",
        *[f"- {issue}" for issue in issues],
        "",
        "Token/lượt gọi/ký tự là tổng của mọi lượt; chất lượng là trung bình các lượt hoàn tất.",
        "",
        f"| Chỉ số | {baseline['variant']} | {candidate['variant']} | Thay đổi |",
        "|---|---|---|---|",
    ]
    for field in ("completion_rate", *SUMMARY_FIELDS):
        value_before = before.get(field)
        value_after = after.get(field)
        change = ""
        if (
            not issues
            and isinstance(value_before, int | float)
            and isinstance(value_after, int | float)
            and value_before
        ):
            change = f"{(value_after - value_before) / value_before:+.0%}"
        lines.append(f"| {field} | {value_before} | {value_after} | {change} |")
    return "\n".join(lines)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def _code_manifest() -> dict[str, Any]:
    api_root = Path(__file__).resolve().parents[2]
    source_files = [
        path for path in (api_root / "app").rglob("*.py") if "__pycache__" not in path.parts
    ]
    source_hashes = {
        str(path.relative_to(api_root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(source_files)
    }
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=api_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        revision = None
    lock = api_root / "uv.lock"
    return {
        "revision": revision,
        "source_sha256": _digest(source_hashes),
        "lock_sha256": hashlib.sha256(lock.read_bytes()).hexdigest() if lock.exists() else None,
    }


class FrozenCorpus:
    """Deterministic search/fetch over a fixed public source pool; never falls back to the web."""

    def __init__(self, sources: list[dict[str, str]]):
        _validate_corpus_sources(sources)
        self.sources = {source["url"]: source for source in sources}
        self.snapshot_sha256 = _digest(sources)
        self.name = f"frozen_corpus_{self.snapshot_sha256[:10]}"

    def search(self, query: str, *, limit: int) -> list[SearchHit]:
        ranked = sorted(
            self.sources.values(),
            key=lambda source: (
                -text_relevance(content_terms(query), f"{source['title']} {source['text']}"),
                source["url"],
            ),
        )
        return [
            SearchHit(
                url=source["url"],
                title=source["title"],
                snippet=source["text"],
                provider=self.name,
                rank=index,
            )
            for index, source in enumerate(ranked[:limit], start=1)
        ]

    def fetch(self, url: str) -> runner.FetchedPage:
        if url not in self.sources:
            raise ValueError("Nguồn không có trong corpus cố định")
        source = self.sources[url]
        return runner.FetchedPage(url=url, title=source["title"], text=source["text"])


def _corpus_entry(db: Session, run_id: str, question: dict[str, Any]) -> dict[str, Any]:
    run = db.get(ResearchRun, run_id)
    if run is None or run.created_by != runner.EVAL_ACTOR:
        raise ValueError("Chỉ xuất nguồn từ lượt đánh giá riêng")
    if " ".join(run.question.split()) != " ".join(question["question"].split()):
        raise ValueError("Câu hỏi và lượt chạy không khớp")
    sources = [
        {"url": source.url, "title": source.title, "text": source.content_text}
        for source in db.query(ResearchRunSource).filter_by(run_id=run_id)
        if source.content_text
        and source.url.startswith(("http://", "https://"))
        and source.provider != "internal_kb"
        and source.research_item_id is None
    ]
    if not sources:
        raise ValueError("Không có nguồn công khai đọc được cho câu hỏi")
    _validate_corpus_sources(sources)
    return {
        "question_sha256": _digest(question),
        "sources": sorted(sources, key=lambda s: s["url"]),
    }


def write_corpus_from_runs(
    db: Session,
    path: Path,
    question_run_ids: dict[str, str],
    *,
    questions_path: Path = DEFAULT_QUESTIONS,
) -> dict[str, Any]:
    """Export already fetched public eval sources without new model calls or DB writes.

    Full source text belongs outside the repository/AI_LOGS. Only hashes and run metrics may be
    committed as evidence. An exclusive create prevents overwriting another snapshot or a symlink.
    """
    questions = {q["id"]: q for q in load_questions(questions_path)}
    entries = {
        qid: _corpus_entry(db, run_id, questions[qid]) for qid, run_id in question_run_ids.items()
    }
    corpus = {"version": CORPUS_VERSION, "questions": entries, "sha256": _digest(entries)}
    encoded = json.dumps(corpus, ensure_ascii=False).encode()
    if len(encoded) > MAX_CORPUS_BYTES:
        raise ValueError("Corpus vượt giới hạn kích thước")
    repo_root = _repository_root()
    path = path.expanduser().absolute()
    if path.resolve().is_relative_to(repo_root):
        raise ValueError("Lưu corpus bên ngoài repository và AI_LOGS")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(encoded)
    return corpus


def _repository_root() -> Path:
    # Source checkout: apps/api/app/evaluation/...; packaged container: /app/app/evaluation/....
    api_root = Path(__file__).resolve().parents[2]
    return next(
        (
            parent
            for parent in (api_root, *api_root.parents)
            if (parent / "AGENTS.md").is_file() or (parent / ".git").exists()
        ),
        api_root,
    )


def _validate_corpus_sources(sources: Any) -> None:
    if not isinstance(sources, list) or not 1 <= len(sources) <= 200:
        raise ValueError("Danh sách nguồn corpus không hợp lệ")
    seen: set[str] = set()
    for source in sources:
        if not isinstance(source, dict) or set(source) != {"url", "title", "text"}:
            raise ValueError("Nguồn corpus sai cấu trúc")
        if any(
            not isinstance(source[key], str) or len(source[key]) > bound
            for key, bound in (("url", 2000), ("title", 500), ("text", 60_000))
        ):
            raise ValueError("Nguồn corpus vượt giới hạn")
        url = source["url"]
        try:
            parsed = urlsplit(url)
            host = (parsed.hostname or "").lower()
            valid = (
                parsed.scheme in {"http", "https"}
                and bool(host)
                and parsed.username is None
                and parsed.password is None
                and parsed.port != 0
                and not parsed.fragment
                and not any(ord(char) < 33 for char in url)
                and host != "localhost"
                and not host.endswith((".localhost", ".local", ".internal"))
            )
            try:
                valid = valid and ipaddress.ip_address(host).is_global
            except ValueError:
                pass  # No DNS/network calls while replaying a frozen public corpus.
        except ValueError:
            valid = False
        if not valid or not source["text"].strip() or url in seen:
            raise ValueError("Nguồn corpus cần URL HTTP(S) công khai, duy nhất và văn bản đọc được")
        seen.add(url)


def _load_corpus(path: Path, questions: list[dict[str, Any]]) -> dict[str, Any]:
    if path.stat().st_size > MAX_CORPUS_BYTES:
        raise ValueError("Corpus vượt giới hạn kích thước")
    corpus = json.loads(path.read_text(encoding="utf-8"))
    if corpus.get("version") != CORPUS_VERSION or corpus.get("sha256") != _digest(
        corpus.get("questions")
    ):
        raise ValueError("Corpus sai phiên bản hoặc checksum")
    for question in questions:
        entry = corpus["questions"].get(question["id"], {})
        if entry.get("question_sha256") != _digest(question) or not entry.get("sources"):
            raise ValueError("Corpus thiếu nguồn hoặc khác phiên bản câu hỏi")
        _validate_corpus_sources(entry["sources"])
    return corpus


def run_eval(
    db: Session,
    *,
    variant: str,
    only: set[str] | None = None,
    questions_path: Path = DEFAULT_QUESTIONS,
    corpus: Path | None = None,
    capture_corpus: Path | None = None,
    stop_on_provider_error: bool = False,
) -> dict[str, Any]:
    # Lệnh vận hành chạy được kể cả khi tính năng chưa bật cho người dùng.
    previously_enabled = settings.research_agent_enabled
    # Mỗi lần eval một "muối" cache mới: biến thể sau không hưởng cache của biến thể trước.
    salt = uuid.uuid4().hex
    questions = load_questions(questions_path, only)
    if not questions:
        raise ValueError("Không có câu hỏi được chọn")
    if corpus is not None and capture_corpus is not None:
        raise ValueError("Chọn đọc corpus hoặc ghi corpus, không chọn cả hai")
    frozen = _load_corpus(corpus, questions) if corpus is not None else None
    manifest = {
        "version": MANIFEST_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "questions_version": json.loads(questions_path.read_text())["version"],
        "questions_sha256": hashlib.sha256(questions_path.read_bytes()).hexdigest(),
        "selected_questions_sha256": _digest(questions),
        "question_ids": [q["id"] for q in questions],
        "full_question_ids": [q["id"] for q in load_questions(questions_path)],
        "code": _code_manifest(),
        "config": {key: getattr(settings, key) for key in EVAL_CONFIG_FIELDS},
        "variant_flags": runner.VARIANTS[variant],
        "prompt_versions": dict(runner.PROMPT_VERSIONS),
        "cache_policy": "cold-per-evaluation",
        "quality_gates": QUALITY_GATES,
        "corpus": {"mode": "frozen", "sha256": frozen["sha256"]} if frozen else {"mode": "live"},
    }
    settings.research_agent_enabled = True
    stopped = None
    try:
        results = []
        for question in questions:
            if frozen:
                pool = FrozenCorpus(frozen["questions"][question["id"]]["sources"])

                def advance(db, run, pool=pool):
                    return runner.advance_research_run(db, run, providers=[pool], fetch=pool.fetch)

                result = run_question(db, question, variant, cache_salt=salt, advance=advance)
                result["selected_sources_sha256"] = result["source_snapshot_sha256"]
                result["source_snapshot_sha256"] = pool.snapshot_sha256
            else:
                result = run_question(db, question, variant, cache_salt=salt)
            results.append(result)
            if (
                stop_on_provider_error
                and result.get("status") == "failed"
                and result.get("error_code") in PROVIDER_STOP_CODES
            ):
                stopped = {"question_id": question["id"], "error_code": result["error_code"]}
                break
    finally:
        settings.research_agent_enabled = previously_enabled
    if capture_corpus is not None and stopped is None:
        write_corpus_from_runs(
            db,
            capture_corpus,
            {r["id"]: r["run_id"] for r in results},
            questions_path=questions_path,
        )
    manifest["provider_models"] = sorted(
        {(r.get("provider"), r.get("model")) for r in results}, key=str
    )
    return {
        "variant": variant,
        "manifest": manifest,
        "results": results,
        "summary": summarize(results),
        **({"stopped": stopped} if stopped else {}),
    }
