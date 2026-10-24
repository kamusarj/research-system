"""Chặn đầu ra AI chứa chuỗi giống thông tin xác thực trước khi lưu hay hiển thị.

Nội dung web/tài liệu không tin cậy có thể chứa lệnh tiêm (prompt injection) bảo CLI đọc tệp
đăng nhập trong sandbox rồi chép vào câu trả lời; câu trả lời đó sẽ vào cơ sở dữ liệu dùng chung.
Lớp này không thay thế sandbox, nhưng không để khóa lọt ra ngoài nếu sandbox bị vượt.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

CREDENTIAL_PATTERNS: dict[str, re.Pattern[str]] = {
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    "openai-key": re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}"),
    "anthropic-key": re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"),
    "google-key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private-key": re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"),
    "oauth-field": re.compile(
        r"[\"']?(?:refresh_token|access_token|id_token)[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9._-]{20,}"
    ),
}


class CredentialInOutputError(ValueError):
    """Đầu ra bị từ chối; là ValueError để đi theo đường xử lý 'phản hồi AI không hợp lệ'."""


def _strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _strings(item)


def credential_kinds(value: Any) -> list[str]:
    found: set[str] = set()
    for text in _strings(value):
        for name, pattern in CREDENTIAL_PATTERNS.items():
            if pattern.search(text):
                found.add(name)
    return sorted(found)


REDACTION = "[REDACTED_CREDENTIAL]"


def redact_credentials(value: Any, *, provider: str) -> Any:
    """Thay chuỗi giống khóa bằng nhãn che. Che thay vì từ chối: tài liệu hướng dẫn hay chứa khóa
    mẫu, từ chối cả câu trả lời sẽ làm hỏng mọi lượt xử lý nguồn đó."""
    kinds = credential_kinds(value)
    if not kinds:
        return value
    logger.warning(
        "AI output credential-like content redacted",
        extra={
            "action": "ai.output.credential_redacted",
            "provider": provider,
            "outcome": ",".join(kinds),
        },
    )
    return _redact(value)


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        for pattern in CREDENTIAL_PATTERNS.values():
            value = pattern.sub(REDACTION, value)
        return value
    if isinstance(value, dict):
        return {key: _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def reject_credentials(value: Any, *, provider: str) -> None:
    kinds = credential_kinds(value)
    if kinds:
        # Không ghi giá trị; chỉ loại chuỗi để người vận hành điều tra nguồn đã đưa vào.
        logger.warning(
            "AI output rejected: credential-like content",
            extra={
                "action": "ai.output.credential_blocked",
                "provider": provider,
                "outcome": ",".join(kinds),
            },
        )
        raise CredentialInOutputError("AI output contained credential-like content")
