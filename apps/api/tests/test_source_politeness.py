"""Be a well-behaved reader, and do not re-download what has not changed.

A queue of twenty links from one domain previously hit that domain as fast as the worker
could issue requests, and a retry always downloaded the whole page again.
"""

import httpx
import pytest

from app.core.config import settings
from app.services.sources.http import (
    NotModified,
    conditional_headers,
    fetch_public,
)
from app.services.sources.politeness import HostRateLimiter, RobotsPolicy, reset_politeness
from tests.test_sources import _mock_fetch


@pytest.fixture(autouse=True)
def isolated_politeness():
    reset_politeness()
    yield
    reset_politeness()


class TestHostRateLimit:
    def test_the_first_request_to_a_host_is_not_delayed(self):
        limiter = HostRateLimiter(min_interval_seconds=1.0)

        assert limiter.delay_for("example.com", now=100.0) == 0.0

    def test_a_second_request_to_the_same_host_waits(self):
        limiter = HostRateLimiter(min_interval_seconds=1.0)
        limiter.delay_for("example.com", now=100.0)

        assert limiter.delay_for("example.com", now=100.0) == pytest.approx(1.0)

    def test_requests_queue_rather_than_collapse_onto_one_slot(self):
        limiter = HostRateLimiter(min_interval_seconds=1.0)
        delays = [limiter.delay_for("example.com", now=100.0) for _ in range(3)]

        assert delays == pytest.approx([0.0, 1.0, 2.0])

    def test_a_busy_host_does_not_hold_up_a_different_one(self):
        limiter = HostRateLimiter(min_interval_seconds=1.0)
        limiter.delay_for("busy.example", now=100.0)

        assert limiter.delay_for("other.example", now=100.0) == 0.0

    def test_the_limit_can_be_switched_off(self):
        limiter = HostRateLimiter(min_interval_seconds=0)
        limiter.delay_for("example.com", now=100.0)

        assert limiter.delay_for("example.com", now=100.0) == 0.0


class TestRobots:
    @staticmethod
    def _serve(monkeypatch, handler) -> None:
        # robots.txt đi qua transport ghim IP như mọi lần tải nguồn; giả lập chính transport đó.
        monkeypatch.setattr(
            "app.services.sources.http.public_transport", lambda: httpx.MockTransport(handler)
        )

    def _policy(self, monkeypatch, body: str | None, status_code: int = 200) -> RobotsPolicy:
        def handler(request):
            if body is None:
                raise httpx.ConnectError("robots.txt is unreachable")
            return httpx.Response(status_code, text=body, request=request)

        self._serve(monkeypatch, handler)
        monkeypatch.setattr(settings, "intake_respect_robots", True)
        return RobotsPolicy("ResearchSystem")

    def test_a_disallowed_path_is_refused(self, monkeypatch):
        policy = self._policy(monkeypatch, "User-agent: *\nDisallow: /private/")

        assert policy.allows("https://example.com/public/article") is True
        assert policy.allows("https://example.com/private/secret") is False

    def test_an_unreachable_robots_file_does_not_block_collection(self, monkeypatch):
        policy = self._policy(monkeypatch, None)

        # An outage on their side must not look like a publisher's decision.
        assert policy.allows("https://example.com/article") is True

    def test_a_missing_robots_file_permits_everything(self, monkeypatch):
        policy = self._policy(monkeypatch, "", status_code=404)

        assert policy.allows("https://example.com/article") is True

    def test_the_policy_is_ignored_when_the_setting_is_off(self, monkeypatch):
        policy = self._policy(monkeypatch, "User-agent: *\nDisallow: /")
        monkeypatch.setattr(settings, "intake_respect_robots", False)

        assert policy.allows("https://example.com/anything") is True

    def test_robots_is_fetched_once_per_host(self, monkeypatch):
        calls: list[str] = []

        def handler(request):
            calls.append(str(request.url))
            return httpx.Response(200, text="User-agent: *\nDisallow:", request=request)

        self._serve(monkeypatch, handler)
        monkeypatch.setattr(settings, "intake_respect_robots", True)
        policy = RobotsPolicy("ResearchSystem")

        policy.allows("https://example.com/a")
        policy.allows("https://example.com/b")

        assert len(calls) == 1


class TestConditionalGet:
    def test_stored_validators_become_conditional_headers(self):
        headers = conditional_headers(
            {"etag": '"v1"', "last-modified": "Mon, 01 Jan 2026 00:00:00 GMT"}
        )

        assert headers["If-None-Match"] == '"v1"'
        assert headers["If-Modified-Since"] == "Mon, 01 Jan 2026 00:00:00 GMT"

    def test_nothing_is_sent_without_stored_validators(self):
        assert conditional_headers(None) == {}
        assert conditional_headers({}) == {}

    def test_the_feature_can_be_switched_off(self, monkeypatch):
        monkeypatch.setattr(settings, "intake_conditional_get", False)

        assert conditional_headers({"etag": '"v1"'}) == {}

    def test_a_response_records_the_validators_a_later_request_needs(self, monkeypatch):
        def handler(request):
            return httpx.Response(
                200,
                headers={"content-type": "text/html", "ETag": '"v1"'},
                content=b"<p>An article body long enough to be treated as real content.</p>",
                request=request,
            )

        _mock_fetch(monkeypatch, handler)

        resource = fetch_public("https://publisher.example/article", {"text/html"})

        assert resource.validators == {"etag": '"v1"'}

    def test_an_unchanged_source_is_reported_rather_than_downloaded_again(self, monkeypatch):
        seen: dict[str, str] = {}

        def handler(request):
            seen.update(request.headers)
            return httpx.Response(304, request=request)

        _mock_fetch(monkeypatch, handler)

        with pytest.raises(NotModified):
            fetch_public(
                "https://publisher.example/article",
                {"text/html"},
                validators={"etag": '"v1"'},
            )

        assert seen["if-none-match"] == '"v1"'
