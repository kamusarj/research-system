from concurrent.futures import ThreadPoolExecutor

from app.core.runtime_controls import SlidingWindowLimiter


def test_expired_login_identities_are_reclaimed_on_unrelated_traffic():
    now = [0.0]
    limiter = SlidingWindowLimiter(clock=lambda: now[0])
    for index in range(1000):
        limiter.record("login-failure", f"person-{index}@fixture.invalid", 60)
    assert len(limiter._events) == 1000

    now[0] = 3600
    limiter.consume("chat", "active-user", 5, 60)

    assert set(limiter._events) == {("chat", "active-user")}
    assert len(limiter._windows) == len(limiter._deadlines) == len(limiter._expiry) == 1


def test_expiring_an_old_heap_entry_does_not_reset_a_live_limit():
    now = [0.0]
    limiter = SlidingWindowLimiter(clock=lambda: now[0])
    assert limiter.consume("chat", "user", 2, 60)[0]
    now[0] = 30
    assert limiter.consume("chat", "user", 2, 60)[0]
    now[0] = 61
    assert limiter.consume("chat", "user", 2, 60)[0]
    assert limiter.consume("chat", "user", 2, 60) == (False, 0, 29)
    now[0] = 91
    assert limiter.consume("chat", "user", 2, 60)[0]


def test_recent_cleans_other_identities_but_keeps_active_failure_count():
    now = [0.0]
    limiter = SlidingWindowLimiter(clock=lambda: now[0])
    limiter.record("failed", "old-user", 10)
    now[0] = 5
    limiter.record("failed", "active-user", 60)
    now[0] = 11

    assert limiter.recent("failed", "active-user", 60) == 1
    assert ("failed", "old-user") not in limiter._events
    now[0] = 65
    assert limiter.recent("failed", "active-user", 60) == 0
    assert not limiter._events and not limiter._deadlines and not limiter._expiry


def test_limiter_cleanup_remains_atomic_under_concurrent_requests():
    limiter = SlidingWindowLimiter(clock=lambda: 100.0)
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda _: limiter.consume("chat", "user", 7, 60), range(100)))
    assert sum(allowed for allowed, _, _ in results) == 7
    assert limiter.recent("chat", "user", 60) == 7
    limiter.clear()
    assert not limiter._events and not limiter._windows and not limiter._expiry
