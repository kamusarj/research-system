"""A per-user request budget, so one channel cannot flood the intake worker."""

from __future__ import annotations

from collections import deque


class PerUserRateLimit:
    """Allow N actions per user per window, measured on a clock the caller supplies.

    Time is injected rather than read from the module so the behaviour can be tested
    without sleeping, and so a monotonic clock can be used in production.
    """

    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self.limit = max(1, limit)
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = {}

    def allow(self, user_id: str, now: float) -> bool:
        events = self._events.setdefault(user_id, deque())
        while events and now - events[0] >= self.window_seconds:
            events.popleft()
        if len(events) >= self.limit:
            return False
        events.append(now)
        return True

    def retry_after(self, user_id: str, now: float) -> float:
        events = self._events.get(user_id)
        if not events:
            return 0.0
        return max(0.0, self.window_seconds - (now - events[0]))
