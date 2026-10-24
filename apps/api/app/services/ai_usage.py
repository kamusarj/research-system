"""Thu số token và độ trễ của từng lời gọi AI để đo chi phí trước/sau tối ưu.

Nhà cung cấp gọi `report_usage` ngay sau khi nhận phản hồi; `provider_observation` gom số liệu
trong phạm vi của nó rồi ghi một dòng `ai_call_metrics`. Không lưu prompt, phản hồi hay khóa.
"""

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

logger = logging.getLogger(__name__)

USAGE_FIELDS = ("input_tokens", "output_tokens", "cached_input_tokens", "prompt_chars")

_current: ContextVar[dict[str, Any] | None] = ContextVar("ai_call_usage", default=None)


def report_usage(
    *,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cached_input_tokens: int | None = None,
    prompt_chars: int | None = None,
    cache_hit: bool = False,
) -> None:
    """Cộng dồn vào lời gọi đang được quan sát; ngoài phạm vi quan sát thì bỏ qua."""
    bucket = _current.get()
    if bucket is None:
        return
    values = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cached_input_tokens": cached_input_tokens,
        "prompt_chars": prompt_chars,
    }
    for key, value in values.items():
        if isinstance(value, int) and value >= 0:
            bucket[key] = bucket.get(key, 0) + value
    if cache_hit:
        bucket["cache_hit"] = True


def report_usage_dict(usage: dict[str, Any] | None, *, prompt_chars: int | None = None) -> None:
    usage = usage or {}
    report_usage(
        input_tokens=_int(usage.get("input_tokens")),
        output_tokens=_int(usage.get("output_tokens")),
        cached_input_tokens=_int(usage.get("cached_input_tokens")),
        prompt_chars=prompt_chars,
    )


def usage_from_openai_responses(payload: dict[str, Any]) -> dict[str, int | None]:
    usage = payload.get("usage") or {}
    details = usage.get("input_tokens_details") or {}
    return {
        "input_tokens": _int(usage.get("input_tokens")),
        "output_tokens": _int(usage.get("output_tokens")),
        "cached_input_tokens": _int(details.get("cached_tokens")),
    }


def usage_from_chat_completions(payload: dict[str, Any]) -> dict[str, int | None]:
    usage = payload.get("usage") or {}
    details = usage.get("prompt_tokens_details") or {}
    cached = _int(details.get("cached_tokens"))
    if cached is None:
        cached = _int(usage.get("prompt_cache_hit_tokens"))  # DeepSeek
    return {
        "input_tokens": _int(usage.get("prompt_tokens")),
        "output_tokens": _int(usage.get("completion_tokens")),
        "cached_input_tokens": cached,
    }


def usage_from_gemini(payload: dict[str, Any]) -> dict[str, int | None]:
    usage = payload.get("usageMetadata") or {}
    return {
        "input_tokens": _int(usage.get("promptTokenCount")),
        "output_tokens": _int(usage.get("candidatesTokenCount")),
        "cached_input_tokens": _int(usage.get("cachedContentTokenCount")),
    }


def usage_from_ollama(payload: dict[str, Any]) -> dict[str, int | None]:
    return {
        "input_tokens": _int(payload.get("prompt_eval_count")),
        "output_tokens": _int(payload.get("eval_count")),
        "cached_input_tokens": None,
    }


@contextmanager
def collect_usage() -> Iterator[dict[str, Any]]:
    bucket: dict[str, Any] = {}
    token = _current.set(bucket)
    try:
        yield bucket
    finally:
        _current.reset(token)


def _default_recorder(row: dict[str, Any]) -> None:
    from app.db import SessionLocal
    from app.models import AICallMetric

    with SessionLocal() as db:
        db.add(AICallMetric(**row))
        db.commit()


_recorder: Callable[[dict[str, Any]], None] = _default_recorder


def set_recorder(recorder: Callable[[dict[str, Any]], None]) -> Callable[[dict[str, Any]], None]:
    """Thay nơi ghi số liệu (dùng trong test); trả về recorder cũ để khôi phục."""
    global _recorder
    previous = _recorder
    _recorder = recorder
    return previous


def record_call(row: dict[str, Any]) -> None:
    # Đo lường không được làm hỏng tác vụ chính: lỗi ghi chỉ được ghi log.
    try:
        _recorder(row)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "AI call metric was not recorded",
            extra={"action": "ai.metric.failed", "error_type": type(exc).__name__},
        )


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
