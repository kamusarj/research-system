"""Kiểm tra bản nháp của writer và dựng báo cáo Markdown có trích dẫn bấm được.

Writer chọn và sắp xếp mã nhận định; máy chủ lấy nguyên văn nhận định đã kiểm chứng để dựng
nội dung và gắn link nguồn. Không dùng độ trùng từ làm bằng chứng cho một cách diễn đạt mới.
"""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.services.research_agent.schemas import (
    PERSPECTIVE_LABELS,
    PERSPECTIVES,
    ReportDraft,
)

_CITATION_GROUP = re.compile(r"(?:\s*\[\d+\]\((?:https?://|/research/)[^)\s]*\))+")
META_HEADINGS = ("Khoảng trống bằng chứng", "Nguồn", "Phương pháp")


@dataclass
class VerifiedClaim:
    id: str
    source_id: str
    perspective: str
    text: str
    quote: str


@dataclass
class SourceRef:
    id: str
    url: str
    title: str
    domain: str
    provider: str
    fetched_at: datetime | None = None


@dataclass
class ValidatedSentence:
    text: str
    claim_ids: list[str]


@dataclass
class ValidatedReport:
    title: str
    sections: dict[str, list[ValidatedSentence]]
    violations: dict[str, int] = field(default_factory=dict)
    total_sentences: int = 0
    accepted_draft_sentences: int = 0

    @property
    def kept_sentences(self) -> int:
        return sum(len(sentences) for sentences in self.sections.values())


def validate_draft(draft: ReportDraft, claims: dict[str, VerifiedClaim]) -> ValidatedReport:
    """Use the writer only for selection/order, never for new factual wording.

    A valid claim ID does not establish entailment of the proposed sentence. Rendering the
    original verified text also prevents a correct sentence hiding a second unsupported assertion.
    Keep one claim per cited block, and preserve its verified perspective outside the summary.
    """
    report = ValidatedReport(title="Báo cáo nghiên cứu", sections={})
    violations: dict[str, int] = {}
    seen: set[tuple[str, str]] = set()
    for section in draft.sections:
        for sentence in section.sentences:
            report.total_sentences += 1
            valid_ids = [
                claim_id for claim_id in dict.fromkeys(sentence.claim_ids) if claim_id in claims
            ]
            if not valid_ids:
                violations["no_verified_claim"] = violations.get("no_verified_claim", 0) + 1
                continue
            accepted = False
            for claim_id in valid_ids:
                claim = claims[claim_id]
                if section.perspective not in {"summary", claim.perspective}:
                    violations["wrong_perspective"] = violations.get("wrong_perspective", 0) + 1
                    continue
                text = " ".join(claim.text.split())
                if not text:
                    violations["empty_verified_claim"] = (
                        violations.get("empty_verified_claim", 0) + 1
                    )
                    continue
                identity = (section.perspective, claim_id)
                if identity in seen:
                    continue
                seen.add(identity)
                accepted = True
                report.sections.setdefault(section.perspective, []).append(
                    ValidatedSentence(text=text, claim_ids=[claim_id])
                )
            if accepted:
                report.accepted_draft_sentences += 1
                if (
                    len(valid_ids) != 1
                    or sentence.text.strip() != claims[valid_ids[0]].text.strip()
                ):
                    violations["rewritten_to_verified_claim"] = (
                        violations.get("rewritten_to_verified_claim", 0) + 1
                    )
    report.violations = violations
    return report


def add_supported_sections(
    report: ValidatedReport, claims: dict[str, VerifiedClaim]
) -> list[str]:
    """Fill omitted sections with one original, verified claim per supported perspective."""
    summary_ids = [
        cid for sentence in report.sections.get("summary", []) for cid in sentence.claim_ids
    ]
    added = []
    for claim_id in dict.fromkeys([*summary_ids, *claims]):
        claim = claims[claim_id]
        perspective = claim.perspective
        if perspective not in PERSPECTIVES or report.sections.get(perspective):
            continue
        text = " ".join(claim.text.split())
        if text:
            report.sections[perspective] = [ValidatedSentence(text=text, claim_ids=[claim_id])]
            added.append(perspective)
    return added


def number_sources(
    report: ValidatedReport, claims: dict[str, VerifiedClaim], sources: dict[str, SourceRef]
) -> dict[str, int]:
    """Đánh số nguồn theo thứ tự xuất hiện đầu tiên trong báo cáo."""
    order: dict[str, int] = {}
    for perspective in ("summary", *PERSPECTIVES):
        for sentence in report.sections.get(perspective, []):
            for claim_id in sentence.claim_ids:
                source_id = claims[claim_id].source_id
                if source_id in sources and source_id not in order:
                    order[source_id] = len(order) + 1
    return order


def render_markdown(
    *,
    question: str,
    report: ValidatedReport,
    claims: dict[str, VerifiedClaim],
    sources: dict[str, SourceRef],
    numbering: dict[str, int],
    method: dict[str, Any],
    generated_at: datetime | None = None,
) -> str:
    generated_at = generated_at or datetime.now(UTC)
    lines = [
        f"# {markdown_text(report.title)}",
        "",
        f"> **Câu hỏi:** {question}",
        ">",
        "> Báo cáo nháp do AI tổng hợp từ nguồn đã kiểm chứng trích dẫn; cần người duyệt trước "
        f"khi xuất bản. Tạo lúc {generated_at:%Y-%m-%d %H:%M} UTC.",
        "",
    ]
    for perspective in ("summary", *PERSPECTIVES):
        sentences = report.sections.get(perspective)
        if not sentences:
            continue
        lines += [f"## {PERSPECTIVE_LABELS[perspective]}", ""]
        rendered = []
        for sentence in sentences:
            cited = []
            for claim_id in sentence.claim_ids:
                source = sources[claims[claim_id].source_id]
                number = numbering[source.id]
                marker = f"[{number}]({markdown_url(source.url)})"
                if marker not in cited:
                    cited.append(marker)
            rendered.append(f"{markdown_text(sentence.text)} {''.join(cited)}")
        for block in rendered:
            lines += [block, ""]

    covered = {perspective for perspective in PERSPECTIVES if report.sections.get(perspective)}
    available = {claim.perspective for claim in claims.values()}
    missing = [p for p in PERSPECTIVES if p not in covered]
    if missing:
        lines += ["## Khoảng trống bằng chứng", ""]
        lines += [
            f"- {PERSPECTIVE_LABELS[p]}: "
            + (
                "có nhận định đã kiểm chứng, nhưng bản nháp chưa tổng hợp góc nhìn này."
                if p in available
                else "chưa tìm thấy nhận định nào đủ bằng chứng trong các nguồn đã đọc."
            )
            for p in missing
        ]
        lines.append("")

    lines += ["## Nguồn", ""]
    for source_id, number in sorted(numbering.items(), key=lambda pair: pair[1]):
        source = sources[source_id]
        title = markdown_text(source.title) or markdown_text(source.domain)
        accessed = f" · truy cập {source.fetched_at:%Y-%m-%d}" if source.fetched_at else ""
        origin = "kho nội bộ" if source.provider == "internal_kb" else source.domain
        lines.append(f"{number}. [{title}]({markdown_url(source.url)}) — {origin}{accessed}")
    lines.append("")

    lines += ["## Phương pháp", ""]
    lines += [f"- {key}: {value}" for key, value in method.items()]
    lines.append("")
    return "\n".join(lines)


def citation_coverage(markdown: str) -> dict[str, int]:
    """Đếm câu nội dung có/không có trích dẫn (bỏ qua tiêu đề, trích khối và mục siêu dữ liệu).

    Một câu là đoạn văn bản đứng trước một nhóm trích dẫn `[n](url)`; phần văn bản còn lại
    sau nhóm trích dẫn cuối của dòng là câu không có nguồn. Chỉ tách theo nhóm trích dẫn nên
    dấu ngoặc bình thường trong câu (ví dụ "(AI)") không bị hiểu nhầm là ranh giới câu.
    """
    cited = uncited = 0
    in_meta = False
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            in_meta = stripped[3:] in META_HEADINGS
            continue
        if in_meta or not stripped or stripped.startswith(("#", ">")):
            continue
        pieces = _CITATION_GROUP.split(stripped)
        cited += sum(1 for piece in pieces[:-1] if _has_words(piece))
        uncited += 1 if _has_words(pieces[-1]) else 0
    return {"cited_sentences": cited, "uncited_sentences": uncited}


def _has_words(text: str) -> bool:
    return bool(re.search(r"\w", text))


_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+!|<>~])")


def markdown_text(value: str) -> str:
    """Văn bản lấy từ nguồn (tiêu đề) đặt vào Markdown: một dòng, ký tự định dạng được thoát."""
    return _MARKDOWN_SPECIAL.sub(r"\\\1", " ".join(value.split()))


def markdown_url(value: str) -> str:
    return value.replace(" ", "%20").replace("(", "%28").replace(")", "%29")
