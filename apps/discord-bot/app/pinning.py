"""Pure validation rules for Discord message pin requests."""

from __future__ import annotations

MAX_DISCORD_SNOWFLAKE = (1 << 64) - 1


def parse_message_id(value: str) -> int | None:
    """Parse one unsigned Discord snowflake without accepting Unicode lookalike digits."""

    normalized = (value or "").strip()
    if not normalized or not normalized.isascii() or not normalized.isdigit():
        return None
    parsed = int(normalized)
    if parsed <= 0 or parsed > MAX_DISCORD_SNOWFLAKE:
        return None
    return parsed
