"""Be a well-behaved reader of other people's servers.

Two things a collector owes a publisher: not hammering them, and respecting a stated
preference not to be crawled. Neither was previously enforced, so a queue of twenty links
from one domain hit it as fast as the worker could run.

State is per process. The worker is a single process today; if it is ever scaled out, this
becomes a per-replica budget and should move to shared storage. That trade is deliberate —
a local limit that works now beats a distributed one that does not exist.
"""

from __future__ import annotations

import threading
import time
import urllib.robotparser
from urllib.parse import urlparse, urlunparse

import httpx

from app.core.config import settings

ROBOTS_MAX_BYTES = 512 * 1024


def host_of(url: str) -> str:
    return (urlparse(url).hostname or "").casefold()


class HostRateLimiter:
    """Space out requests to any one host, without blocking requests to other hosts."""

    def __init__(self, min_interval_seconds: float) -> None:
        self.min_interval_seconds = max(0.0, min_interval_seconds)
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def delay_for(self, host: str, now: float) -> float:
        """How long to wait before touching ``host`` again, and reserve that slot."""

        if not host or self.min_interval_seconds <= 0:
            return 0.0
        with self._lock:
            earliest = self._last.get(host, 0.0) + self.min_interval_seconds
            wait = max(0.0, earliest - now)
            self._last[host] = now + wait
            return wait

    def wait(self, url: str) -> float:
        delay = self.delay_for(host_of(url), time.monotonic())
        if delay > 0:
            time.sleep(delay)
        return delay


class RobotsPolicy:
    """Cache and apply each host's robots.txt.

    A host that cannot be asked is treated as permitting the fetch: refusing on a network
    error would make an unrelated outage look like a publisher's decision.
    """

    def __init__(self, user_agent: str, ttl_seconds: float = 3600.0) -> None:
        self.user_agent = user_agent
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[float, urllib.robotparser.RobotFileParser | None]] = {}
        self._lock = threading.Lock()

    def _parser(self, url: str) -> urllib.robotparser.RobotFileParser | None:
        parsed = urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}".casefold()
        now = time.monotonic()
        with self._lock:
            cached = self._cache.get(host)
            if cached and now - cached[0] < self.ttl_seconds:
                return cached[1]
        parser: urllib.robotparser.RobotFileParser | None = None
        try:
            robots_url = urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
            # Không theo chuyển hướng (có thể trỏ vào mạng nội bộ), kết nối ghim tới địa chỉ công
            # khai đã kiểm (chống DNS rebinding) và chỉ đọc tối đa 512 KiB.
            from app.services.sources.errors import SourceError
            from app.services.sources.http import public_transport

            with httpx.Client(
                transport=public_transport(), timeout=5.0, follow_redirects=False
            ) as client:
                with client.stream("GET", robots_url) as response:
                    if response.status_code < 300:
                        body = b""
                        for chunk in response.iter_bytes():
                            body += chunk
                            if len(body) >= ROBOTS_MAX_BYTES:
                                break
                        parser = urllib.robotparser.RobotFileParser()
                        parser.parse(
                            body[:ROBOTS_MAX_BYTES].decode("utf-8", "replace").splitlines()
                        )
        except (httpx.HTTPError, SourceError):
            parser = None
        with self._lock:
            self._cache[host] = (now, parser)
        return parser

    def allows(self, url: str) -> bool:
        if not settings.intake_respect_robots:
            return True
        parser = self._parser(url)
        if parser is None:
            return True
        return parser.can_fetch(self.user_agent, url)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


_rate_limiter: HostRateLimiter | None = None
_robots: RobotsPolicy | None = None


def host_rate_limiter() -> HostRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = HostRateLimiter(settings.intake_host_min_interval_seconds)
    return _rate_limiter


def robots_policy() -> RobotsPolicy:
    global _robots
    if _robots is None:
        from app.services.sources.http import DEFAULT_USER_AGENT

        _robots = RobotsPolicy(settings.intake_user_agent or DEFAULT_USER_AGENT)
    return _robots


def reset_politeness() -> None:
    """Drop cached state; used by tests and after a settings change."""

    global _rate_limiter, _robots
    _rate_limiter = None
    _robots = None
