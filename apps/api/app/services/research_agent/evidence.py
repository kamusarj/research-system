"""Đối chiếu trích dẫn mô hình chép lại với văn bản nguồn (kiểm chứng tất định, không gọi AI).

Một nhận định chỉ được giữ khi trích dẫn của nó thật sự có trong nguồn: khớp chính xác theo từ,
khớp sau khi chuẩn hóa dấu nháy/gạch/hoa-thường, hoặc khớp gần đúng (≥ 0,9) trên cửa sổ từ với
điều kiện mọi con số trong trích dẫn đều xuất hiện nguyên vẹn.
"""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

_TOKEN = re.compile(r"\S+")
_DIGITS = re.compile(r"\d+(?:[.,]\d+)*")
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
    for index in range(len(words) - 2):
        if tuple(words[index : index + 3]) not in anchors:
            continue
        for start in range(max(0, index - size), index + 1):
            for length in range(max(1, size - slack), size + slack + 1):
                window = words[start : start + length]
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
