import logging
import signal
import threading

from app.core.config import settings
from app.core.observability import configure_logging, exception_fields
from app.db import SessionLocal
from app.services.document_processing import run_pending_documents
from app.services.ingestion import run_pending_submissions
from app.services.research_agent.runner import run_pending_research_steps

if settings.log_format == "json":
    configure_logging()
else:
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("research-worker")

stop_requested = threading.Event()


def _request_stop(signum: int, _frame: object) -> None:
    # Docker sends SIGTERM to PID 1, which Python ignores by default; without this handler the
    # container is killed mid-job after the stop timeout. The current job finishes, then the
    # loop exits; an interrupted lease is recovered by the next worker anyway.
    logger.info("Worker stop requested", extra={"action": "worker.stop", "signal": signum})
    stop_requested.set()


def run_once() -> int:
    """Claim at most one job of each kind so link and document queues are served fairly and a
    stop request is honoured between jobs instead of after a whole batch."""
    with SessionLocal() as db:
        processed = run_pending_submissions(db, max_jobs=1)
        if stop_requested.is_set():
            return processed
        processed += run_pending_documents(db, max_jobs=1)
        if stop_requested.is_set():
            return processed
        # Mỗi vòng chỉ chạy một bước của một lượt nghiên cứu để link/tài liệu không phải chờ lâu.
        return processed + run_pending_research_steps(db, max_steps=1)


def run_forever() -> None:
    logger.info("Research worker started")
    consecutive_failures = 0
    while not stop_requested.is_set():
        try:
            processed = run_once()
            consecutive_failures = 0
            if processed == 0:
                stop_requested.wait(settings.intake_worker_poll_seconds)
        except Exception as exc:
            consecutive_failures += 1
            # The JSON formatter deliberately drops exception messages, which may carry
            # credentials or document content. Type and code location are safe and are
            # what an operator needs to locate the failure.
            logger.error(
                "Intake worker loop failed",
                extra={
                    "action": "worker.loop.failed",
                    "outcome": "error",
                    **exception_fields(exc),
                },
            )
            backoff = min(
                settings.intake_worker_poll_seconds * (2 ** min(consecutive_failures - 1, 5)),
                settings.intake_worker_max_backoff_seconds,
            )
            stop_requested.wait(backoff)
    logger.info("Research worker stopped", extra={"action": "worker.stopped"})


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
    run_forever()
