import logging
import time

from app.core.config import settings
from app.db import SessionLocal
from app.services.ingestion import run_pending_submissions

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("research-worker")


def run_forever() -> None:
    logger.info("Intake worker started")
    while True:
        try:
            with SessionLocal() as db:
                processed = run_pending_submissions(db)
            if processed == 0:
                time.sleep(settings.intake_worker_poll_seconds)
        except Exception:
            logger.exception("Intake worker loop failed")
            time.sleep(settings.intake_worker_poll_seconds)


if __name__ == "__main__":
    run_forever()
