"""Đối chiếu trích dẫn mô hình chép lại với văn bản nguồn (kiểm chứng tất định, không gọi AI).

Một nhận định chỉ được giữ khi trích dẫn của nó thật sự có trong nguồn: khớp chính xác theo từ,
khớp sau khi chuẩn hóa dấu nháy/gạch/hoa-thường, hoặc khớp gần đúng (≥ 0,9) trên cửa sổ từ với
điều kiện mọi con số trong trích dẫn đều xuất hiện nguyên vẹn.
"""

import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.services.research_agent.search import content_terms

_TOKEN = re.compile(r"\S+")
_DIGITS = re.compile(r"\d+(?:[.,]\d+)*")
_ACRONYM = re.compile(r"\b[A-Z][A-Z0-9]{1,7}\b")
_PROPER = re.compile(r"(?<=[a-z,;:\(\s])[A-Z][a-zA-Z0-9]{2,}\b")
_NUMBER_TOKEN = re.compile(r"\d+(?:[.,]\d+)?%?")
_BOILERPLATE = re.compile(
    r"^(?:skip to|home\s*[>/|]|menu|search|subscribe|sign in|log in|cookie|privacy policy|"
    r"terms of (?:service|use)|all rights reserved|copyright|share this|follow us|"
    r"related (?:posts|articles)|table of contents|read more|learn more|contact us)",
    re.IGNORECASE,
)
_PUNCT_MAP = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "…": "...",
        " ": " ",
    }
)
_EDGE_PUNCT = "\"'()[]{}.,;:!?…"


@dataclass(frozen=True)
class QuoteMatch:
    start: int
    end: int
    method: str  # exact | normalized | fuzzy
    score: float


@dataclass(frozen=True)
class EntailmentWindow:
    claim_id: str
    source_id: str
    claim: str
    quote: str
    start: int
    end: int


def compact_entailment_payload(
    windows: list[EntailmentWindow], source_texts: dict[str, str]
) -> str:
    """Share overlapping source context without dropping any original evidence.

    Groups remain source-specific. Each claim keeps its own quote; disjoint
    passages stay separate. Use legacy rows whenever grouping would cost more.
    """

    def encode(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    grouped: dict[str, list[EntailmentWindow]] = {}
    for window in windows:
        grouped.setdefault(window.source_id, []).append(window)
    output = []
    for source_id, claims in grouped.items():
        text = source_texts[source_id]
        legacy = "\n".join(
            encode(
                {
                    "claim_id": row.claim_id,
                    "claim": row.claim,
                    "evidence": text[row.start : row.end],
                }
            )
            for row in claims
        )
        intervals: list[list[int]] = []
        for row in sorted(claims, key=lambda row: row.start):
            if intervals and row.start <= intervals[-1][1]:
                intervals[-1][1] = max(intervals[-1][1], row.end)
            else:
                intervals.append([row.start, row.end])
        shared = encode(
            {
                "evidence": [text[start:end] for start, end in intervals],
                "claims": [
                    {"claim_id": row.claim_id, "claim": row.claim, "quote": row.quote}
                    for row in claims
                ],
            }
        )
        output.append(shared if len(shared) < len(legacy) else legacy)
    return "\n".join(output)


def _normalize_token(token: str) -> str:
    return token.translate(_PUNCT_MAP).casefold().strip(_EDGE_PUNCT)


def _tokens(text: str) -> list[tuple[str, int, int]]:
    return [
        (normalized, match.start(), match.end())
        for match in _TOKEN.finditer(text)
        if (normalized := _normalize_token(match.group()))
    ]


def numbers_in(text: str) -> set[str]:
    """Các con số (bỏ dấu phân cách nghìn/thập phân) để so khớp giữa ngôn ngữ."""
    return {re.sub(r"[.,]", "", value) for value in _DIGITS.findall(text)}


# Từ phủ định: khớp gần đúng không được phép khác nhau ở những từ này (đảo nghĩa câu).
NEGATIONS = frozenset(
    "not no never none without cannot can't don't doesn't isn't aren't won't "
    "không chưa chẳng chả đừng".split()
)
MIN_QUOTE_TOKENS = 6
# Deterministic bound on fuzzy matcher work, independent of machine speed or worker concurrency.
MAX_FUZZY_TOKEN_COMPARISONS = 250_000


def raw_numbers(text: str) -> list[str]:
    """Con số giữ nguyên dấu phân cách (1.5 khác 15) để so trích dẫn với nguồn cùng ngôn ngữ."""
    return _DIGITS.findall(text)


def match_quote(quote: str, text: str, *, min_fuzzy_tokens: int = 8) -> QuoteMatch | None:
    quote = " ".join(quote.split())
    if not quote or not text:
        return None
    # Ranh giới từ ở hai đầu: trích dẫn "20" không được khớp vào giữa "2025".
    pattern = r"(?<!\w)" + r"\s+".join(re.escape(part) for part in quote.split()) + r"(?!\w)"
    exact = re.search(pattern, text)
    if exact:
        return QuoteMatch(exact.start(), exact.end(), "exact", 1.0)

    quote_tokens = [token for token, _, _ in _tokens(quote)]
    text_tokens = _tokens(text)
    if not quote_tokens or not text_tokens:
        return None
    words = [token for token, _, _ in text_tokens]
    size = len(quote_tokens)
    first = quote_tokens[0]
    for index in range(len(words) - size + 1):
        if words[index] == first and words[index : index + size] == quote_tokens:
            return QuoteMatch(
                text_tokens[index][1], text_tokens[index + size - 1][2], "normalized", 1.0
            )

    if size < min_fuzzy_tokens:
        return None
    anchors = {tuple(quote_tokens[offset : offset + 3]) for offset in range(size - 2)}
    slack = max(2, size // 5)
    best: tuple[float, int, int] | None = None
    comparisons = 0
    seen_windows: set[tuple[int, int]] = set()
    for index in range(len(words) - 2):
        if tuple(words[index : index + 3]) not in anchors:
            continue
        for start in range(max(0, index - size), index + 1):
            for length in range(max(1, size - slack), size + slack + 1):
                end = min(len(words), start + length)
                identity = (start, end)
                if identity in seen_windows:
                    continue
                seen_windows.add(identity)
                comparisons += size * (end - start)
                if comparisons > MAX_FUZZY_TOKEN_COMPARISONS:
                    # A partially explored best match is not a complete verification result.
                    return None
                window = words[start:end]
                matcher = SequenceMatcher(None, quote_tokens, window, autojunk=False)
                score = matcher.ratio()
                if best is not None and score <= best[0]:
                    continue
                if not _differences_are_harmless(matcher, quote_tokens, window):
                    continue
                best = (score, start, min(len(words), start + length) - 1)
    if best is None or best[0] < 0.9:
        return None
    score, start_token, end_token = best
    start, end = text_tokens[start_token][1], text_tokens[end_token][2]
    if not set(raw_numbers(quote)) <= set(raw_numbers(text[start:end])):
        return None
    return QuoteMatch(start, end, "fuzzy", round(score, 3))


def _differences_are_harmless(
    matcher: SequenceMatcher, quote_tokens: list[str], window: list[str]
) -> bool:
    """Khác biệt chỉ được là từ thường; không được đụng tới phủ định hay con số."""
    for tag, a_start, a_end, b_start, b_end in matcher.get_opcodes():
        if tag == "equal":
            continue
        changed = quote_tokens[a_start:a_end] + window[b_start:b_end]
        if any(token in NEGATIONS or any(ch.isdigit() for ch in token) for token in changed):
            return False
    return True


def unsupported_numbers(claim: str, evidence: str) -> set[str]:
    """Số trong nhận định không có trong bằng chứng — dấu hiệu mô hình tự thêm dữ liệu."""
    return numbers_in(claim) - numbers_in(evidence)


def _split_spans(
    text: str, sep_pattern: str, start: int = 0, end: int | None = None
) -> list[tuple[int, int]]:
    end = len(text) if end is None else end
    spans: list[tuple[int, int]] = []
    pos = start
    for match in re.finditer(sep_pattern, text[start:end]):
        left, right = pos, start + match.start()
        while left < right and text[left].isspace():
            left += 1
        while right > left and text[right - 1].isspace():
            right -= 1
        if left < right:
            spans.append((left, right))
        pos = start + match.end()
    left, right = pos, end
    while left < right and text[left].isspace():
        left += 1
    while right > left and text[right - 1].isspace():
        right -= 1
    if left < right:
        spans.append((left, right))
    return spans


def _verbatim_spans(text: str, *, max_block: int = 1000) -> list[tuple[int, int]]:
    """Split text into exact (start, end) spans without altering any characters."""
    raw = _split_spans(text, r"\n\s*\n+")
    if len(raw) <= 2:
        raw = _split_spans(text, r"\n+")
    spans: list[tuple[int, int]] = []
    for start, end in raw:
        if end - start <= max_block:
            spans.append((start, end))
            continue
        for line_start, line_end in _split_spans(text, r"\n+", start, end):
            if line_end - line_start <= max_block:
                spans.append((line_start, line_end))
                continue
            cuts = [m.end() for m in re.finditer(r"(?<=[.!?])\s+", text[line_start:line_end])]
            chunk_start = line_start
            last_good = line_start
            for cut in cuts:
                abs_pos = line_start + cut
                if abs_pos - chunk_start > max_block and last_good > chunk_start:
                    chunk_end = last_good
                    while chunk_end > chunk_start and text[chunk_end - 1].isspace():
                        chunk_end -= 1
                    if chunk_end > chunk_start:
                        spans.append((chunk_start, chunk_end))
                    chunk_start = last_good
                    while chunk_start < line_end and text[chunk_start].isspace():
                        chunk_start += 1
                last_good = abs_pos
            if chunk_start < line_end:
                while line_end - chunk_start > max_block:
                    cut_at = text.rfind(" ", chunk_start, chunk_start + max_block)
                    if cut_at <= chunk_start:
                        cut_at = chunk_start + max_block
                    spans.append((chunk_start, cut_at))
                    chunk_start = cut_at
                    while chunk_start < line_end and text[chunk_start].isspace():
                        chunk_start += 1
                if chunk_start < line_end:
                    spans.append((chunk_start, line_end))
    return spans


def select_relevant_passages(
    text: str,
    *,
    query_terms: set[str],
    perspective_terms: set[str],
    max_chars: int = 5000,
) -> str:
    """Select high-signal verbatim spans from source text within max_chars.

    Every chunk separated by blank lines is an exact slice of `text`, preserving verbatim
    quote matching and offsets against the full stored source.
    """
    if not text or max_chars <= 0 or len(text) <= max_chars:
        return text
    spans = _verbatim_spans(text)
    if not spans:
        return text[:max_chars]

    seen_norm: set[str] = set()
    scored: list[tuple[float, int, int, int]] = []
    for idx, (start, end) in enumerate(spans):
        block = text[start:end]
        norm = " ".join(block.casefold().split())
        if norm in seen_norm:
            continue
        seen_norm.add(norm)
        if len(block) < 35 and _BOILERPLATE.match(block):
            continue
        block_terms = content_terms(block)
        q_overlap = len(block_terms & query_terms)
        p_overlap = len(block_terms & perspective_terms)
        nums = min(4, len(_NUMBER_TOKEN.findall(block)))
        acronyms = min(4, len(set(_ACRONYM.findall(block))))
        propers = min(5, len(set(_PROPER.findall(block))))
        words = max(1, len(block.split()))
        if len(block) < 45:
            score = (q_overlap * 1.5 + p_overlap) * 0.4
        else:
            density = (q_overlap * 2.0 + p_overlap * 1.2) / (words / 40.0 + 1.0)
            info = nums * 1.1 + acronyms * 1.0 + propers * 0.6
            lead = 2.0 if idx < 2 and len(block) >= 80 else 0.0
            boilerplate_penalty = -3.0 if _BOILERPLATE.match(block) else 0.0
            score = q_overlap * 2.5 + p_overlap * 1.5 + density + info + lead + boilerplate_penalty
        scored.append((score, idx, start, end))

    picked: list[tuple[int, int, int]] = []
    used = 0
    for _, idx, start, end in sorted(scored, key=lambda item: (-item[0], item[1])):
        sep = 2 if picked else 0
        length = end - start
        if used + sep + length > max_chars:
            if not picked:
                cut_at = text.rfind(" ", start, start + max_chars)
                limit_end = cut_at if cut_at > start else min(end, start + max_chars)
                picked.append((idx, start, limit_end))
                used += limit_end - start
            continue
        picked.append((idx, start, end))
        used += sep + length
        if used >= max_chars - 80:
            break

    if not picked:
        return text[:max_chars]

    picked.sort(key=lambda item: item[0])
    merged: list[tuple[int, int]] = []
    slack = max(0, max_chars - used)
    prev_idx = -2
    for idx, start, end in picked:
        if merged and idx == prev_idx + 1:
            gap = start - merged[-1][1]
            extra = max(0, gap - 2)
            if 0 <= gap <= 4 and extra <= slack:
                merged[-1] = (merged[-1][0], end)
                slack -= extra
                prev_idx = idx
                continue
        merged.append((start, end))
        prev_idx = idx
    return "\n\n".join(text[start:end] for start, end in merged)
