import signal

import pytest

from app import worker


@pytest.fixture(autouse=True)
def reset_stop_flag():
    worker.stop_requested.clear()
    yield
    worker.stop_requested.clear()


def test_run_once_claims_one_job_of_each_kind(monkeypatch):
    calls: list[tuple[str, int]] = []

    def submissions(_db, max_jobs):
        calls.append(("links", max_jobs))
        return 1

    def documents(_db, max_jobs):
        calls.append(("documents", max_jobs))
        return 1

    monkeypatch.setattr(worker, "run_pending_submissions", submissions)
    monkeypatch.setattr(worker, "run_pending_documents", documents)

    assert worker.run_once() == 2
    assert calls == [("links", 1), ("documents", 1)]


def test_stop_request_skips_remaining_queue_and_ends_loop(monkeypatch):
    calls: list[str] = []

    def submissions(_db, max_jobs):
        calls.append("links")
        # A SIGTERM arriving while a job runs must not start the next job.
        worker._request_stop(signal.SIGTERM, None)
        return 1

    def documents(_db, max_jobs):
        calls.append("documents")
        return 0

    monkeypatch.setattr(worker, "run_pending_submissions", submissions)
    monkeypatch.setattr(worker, "run_pending_documents", documents)

    worker.run_forever()

    assert calls == ["links"]
    assert worker.stop_requested.is_set()


def test_loop_survives_job_failure_then_stops(monkeypatch):
    attempts = 0

    def failing_once():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("transient database outage")
        worker.stop_requested.set()
        return 0

    monkeypatch.setattr(worker, "run_once", failing_once)
    monkeypatch.setattr(worker.settings, "intake_worker_poll_seconds", 0.01)

    worker.run_forever()

    assert attempts == 2
