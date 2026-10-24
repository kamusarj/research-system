"""Tổng hợp token/độ trễ theo tác vụ từ `ai_call_metrics` (và lịch sử chat) cho bảng trước/sau."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Integer, case, func, select
from sqlalchemy.orm import Session

from app.models import AICallMetric, ChatMessage


def ai_usage_report(db: Session, *, since_hours: float) -> dict[str, Any]:
    since = datetime.now(UTC) - timedelta(hours=since_hours)
    rows = db.execute(
        select(
            AICallMetric.operation,
            AICallMetric.provider,
            func.count(),
            func.sum(case((AICallMetric.outcome == "success", 1), else_=0)),
            func.avg(AICallMetric.latency_ms),
            func.avg(AICallMetric.input_tokens),
            func.avg(AICallMetric.output_tokens),
            func.sum(AICallMetric.input_tokens),
            func.sum(AICallMetric.output_tokens),
            func.sum(AICallMetric.cached_input_tokens),
            func.sum(AICallMetric.total_tokens),
            func.avg(AICallMetric.prompt_chars),
            func.sum(func.cast(AICallMetric.cache_hit, Integer)),
        )
        .where(AICallMetric.created_at >= since)
        .group_by(AICallMetric.operation, AICallMetric.provider)
        .order_by(AICallMetric.operation)
    ).all()
    operations = [
        {
            "operation": operation,
            "provider": provider,
            "calls": calls,
            "successful_calls": int(successes or 0),
            "avg_latency_ms": _round(avg_latency),
            "avg_input_tokens": _round(avg_input),
            "avg_output_tokens": _round(avg_output),
            "total_input_tokens": int(total_input or 0),
            "total_output_tokens": int(total_output or 0),
            "total_cached_input_tokens": int(total_cached or 0),
            "total_tokens": int(total_tokens or 0),
            "avg_prompt_chars": _round(avg_chars),
            "cache_hits": int(cache_hits or 0),
        }
        for (
            operation,
            provider,
            calls,
            successes,
            avg_latency,
            avg_input,
            avg_output,
            total_input,
            total_output,
            total_cached,
            total_tokens,
            avg_chars,
            cache_hits,
        ) in rows
    ]
    chat = db.execute(
        select(
            func.count(),
            func.avg(ChatMessage.latency_ms),
        ).where(
            ChatMessage.role == "assistant",
            ChatMessage.latency_ms.is_not(None),
            ChatMessage.created_at >= since,
        )
    ).one()
    return {
        "since": since.isoformat(),
        "operations": operations,
        "chat_turns": {"count": chat[0], "avg_latency_ms": _round(chat[1])},
    }


def _round(value: Any) -> float | None:
    return None if value is None else round(float(value), 1)
