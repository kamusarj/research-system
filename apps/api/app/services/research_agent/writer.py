"""Kiểm tra bản nháp của writer và dựng báo cáo Markdown có trích dẫn bấm được.

Writer chỉ trả về câu + mã nhận định; máy chủ mới là nơi gắn link nguồn. Câu không còn nhận định
hợp lệ, có số không nằm trong bằng chứng, hay chèn link/HTML đều bị loại, nên mọi câu nội dung
trong báo cáo đều mang ít nhất một trích dẫn `[n](url)` tới nguồn đã kiểm chứng.
"""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.services.research_agent.evidence import unsupported_numbers
from app.services.research_agent.schemas import (
    PERSPECTIVE_LABELS,
    PERSPECTIVES,
    ReportDraft,
)

_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_URL = re.compile(r"https?://\S+|www\.\S+", re.I)
_HTML = re.compile(r"<[^>]+>")
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

    @property
    def kept_sentences(self) -> int:
        return sum(len(sentences) for sentences in self.sections.values())


def _clean(text: str) -> str:
    text = _LINK.sub(r"\1", text)
    text = _HTML.sub("", _URL.sub("", text))
    text = re.sub(r"\[\d+\]", "", text)  # mô hình tự đánh số trích dẫn: máy chủ sẽ gắn lại
    return " ".join(text.split())


MIN_SUPPORT_RATIO = 0.3
_CONTENT_WORD = re.compile(r"\w{3,}", re.UNICODE)


def support_ratio(text: str, evidence: str) -> float:
    """Tỉ lệ từ nội dung (≥3 ký tự) của câu có trong nhận định/trích dẫn được dẫn."""
    words = {word.casefold() for word in _CONTENT_WORD.findall(text)}
    if not words:
        return 0.0
    available = {word.casefold() for word in _CONTENT_WORD.findall(evidence)}
    return len(words & available) / len(words)


def validate_draft(draft: ReportDraft, claims: dict[str, VerifiedClaim]) -> ValidatedReport:
    report = ValidatedReport(title=_clean(draft.title)[:200] or "Báo cáo nghiên cứu", sections={})
    violations: dict[str, int] = {}
    for section in draft.sections:
        for sentence in section.sentences:
            report.total_sentences += 1
            valid_ids = [
                claim_id for claim_id in dict.fromkeys(sentence.claim_ids) if claim_id in claims
            ]
            if not valid_ids:
                violations["no_verified_claim"] = violations.get("no_verified_claim", 0) + 1
                continue
            text = _clean(sentence.text)
            if not text:
                violations["empty"] = violations.get("empty", 0) + 1
                continue
            evidence = " ".join(f"{claims[i].text} {claims[i].quote}" for i in valid_ids)
            if unsupported_numbers(text, evidence):
                violations["unsupported_number"] = violations.get("unsupported_number", 0) + 1
                continue
            if support_ratio(text, evidence) < MIN_SUPPORT_RATIO:
                # Câu dẫn một nhận định nhưng nói chuyện khác: dấu hiệu bịa hoặc bị dẫn dắt.
                violations["weak_support"] = violations.get("weak_support", 0) + 1
                continue
            report.sections.setdefault(section.perspective, []).append(
                ValidatedSentence(text=text, claim_ids=valid_ids)
            )
    report.violations = violations
    return report


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
        f"# {report.title}",
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
            rendered.append(f"{sentence.text.rstrip()} {''.join(cited)}")
        lines += [" ".join(rendered), ""]

    covered = {perspective for perspective in PERSPECTIVES if report.sections.get(perspective)}
    missing = [PERSPECTIVE_LABELS[p] for p in PERSPECTIVES if p not in covered]
    if missing:
        lines += ["## Khoảng trống bằng chứng", ""]
        lines += [
            f"- {label}: chưa tìm thấy nhận định nào đủ bằng chứng trong các nguồn đã đọc."
            for label in missing
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
