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


def match_quote(quote: str, text: str, *, min_fuzzy_tokens: int = 8) -> QuoteMatch | None:
    quote = " ".join(quote.split())
    if not quote or not text:
        return None
    exact = re.search(r"\s+".join(re.escape(part) for part in quote.split()), text)
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
    best: tuple[float, int, int] | None = None
    for index in range(len(words) - 2):
        if tuple(words[index : index + 3]) not in anchors:
            continue
        for start in range(max(0, index - size), index + 1):
            window = words[start : start + size + 2]
            score = SequenceMatcher(None, quote_tokens, window, autojunk=False).ratio()
            if best is None or score > best[0]:
                best = (score, start, min(len(words), start + size + 2) - 1)
    if best is None or best[0] < 0.9:
        return None
    score, start_token, end_token = best
    start, end = text_tokens[start_token][1], text_tokens[end_token][2]
    if not numbers_in(quote) <= numbers_in(text[start:end]):
        return None
    return QuoteMatch(start, end, "fuzzy", round(score, 3))


def unsupported_numbers(claim: str, evidence: str) -> set[str]:
    """Số trong nhận định không có trong bằng chứng — dấu hiệu mô hình tự thêm dữ liệu."""
    return numbers_in(claim) - numbers_in(evidence)
