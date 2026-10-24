from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path


def main() -> None:
    descriptor, database_path = tempfile.mkstemp(
        prefix="business-ai-receipt-migration-", suffix=".db"
    )
    os.close(descriptor)
    api_root = Path(__file__).resolve().parents[1]
    os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import MetaData, Table, create_engine, func, select, text

    config = Config(str(api_root / "alembic.ini"))
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        command.upgrade(config, "c5a8e2f4b901")
        metadata = MetaData()
        submissions = Table("link_submissions", metadata, autoload_with=engine)
        now = datetime.now(UTC)
        common = {
            "submitted_by": "legacy-user",
            "status": "completed",
            "stage": "completed",
            "review_status": "needs_review",
            "title": None,
            "extracted_markdown": "",
            "content_hash": None,
            "classification": {},
            "source_overrides": {},
            "provider_name": "mistral",
            "model_name": None,
            "auto_approve": False,
            "attempt_count": 1,
            "next_attempt_at": None,
            "started_at": None,
            "finished_at": now,
            "error": None,
            "error_code": None,
            "error_details": {},
            "research_id": None,
            "created_at": now,
            "updated_at": now,
        }
        rows = [
            {
                **common,
                "id": "10000000-0000-0000-0000-000000000001",
                "url": "https://example.com/legacy-one",
                "source_type": "discord",
                "source_ref": "shared-message",
            },
            {
                **common,
                "id": "10000000-0000-0000-0000-000000000002",
                "url": "https://example.com/legacy-two",
                "source_type": "discord",
                "source_ref": "shared-message",
                "status": "pending",
                "stage": "pending",
                "review_status": "not_requested",
                "finished_at": None,
            },
            {
                **common,
                "id": "10000000-0000-0000-0000-000000000003",
                "url": "https://example.com/legacy-three",
                "source_type": "manual",
                "source_ref": None,
                "status": "failed",
                "stage": "failed",
                "review_status": "not_requested",
                "error_code": "FETCH_TIMEOUT",
            },
        ]
        with engine.begin() as connection:
            connection.execute(submissions.insert(), rows)
            before = list(
                connection.execute(
                    select(
                        submissions.c.id,
                        submissions.c.status,
                        submissions.c.stage,
                        submissions.c.review_status,
                        submissions.c.research_id,
                    ).order_by(submissions.c.id)
                )
            )

        command.upgrade(config, "head")
        migrated = MetaData()
        receipts = Table("intake_receipts", migrated, autoload_with=engine)
        items = Table("intake_receipt_items", migrated, autoload_with=engine)
        submissions = Table("link_submissions", migrated, autoload_with=engine)
        with engine.connect() as connection:
            receipt_count = int(connection.scalar(select(func.count()).select_from(receipts)) or 0)
            item_count = int(connection.scalar(select(func.count()).select_from(items)) or 0)
            shared_count = int(
                connection.scalar(
                    select(func.count())
                    .select_from(items.join(receipts, items.c.receipt_id == receipts.c.id))
                    .where(receipts.c.external_occurrence_ref == "shared-message")
                )
                or 0
            )
            missing = int(
                connection.scalar(
                    text(
                        "SELECT COUNT(*) FROM link_submissions s "
                        "LEFT JOIN intake_receipt_items i ON i.link_submission_id = s.id "
                        "WHERE i.id IS NULL"
                    )
                )
                or 0
            )
            after = list(
                connection.execute(
                    select(
                        submissions.c.id,
                        submissions.c.status,
                        submissions.c.stage,
                        submissions.c.review_status,
                        submissions.c.research_id,
                    ).order_by(submissions.c.id)
                )
            )
        assert receipt_count == 2
        assert item_count == 3
        assert shared_count == 2
        assert missing == 0
        assert before == after

        command.downgrade(config, "c5a8e2f4b901")
        command.upgrade(config, "head")
        migrated = MetaData()
        receipts = Table("intake_receipts", migrated, autoload_with=engine)
        with engine.begin() as connection:
            assert int(connection.scalar(select(func.count()).select_from(receipts)) or 0) == 2
            connection.execute(
                receipts.insert(),
                {
                    "id": "20000000-0000-0000-0000-000000000001",
                    "source_type": "api",
                    "source_namespace": "new-runtime",
                    "external_occurrence_ref": "new-event",
                    "delivery_key_hash": "a" * 64,
                    "container_ref": None,
                    "submitted_by": "operator",
                    "external_actor_ref_hash": None,
                    "metadata": {"schema_version": 1},
                    "delivery_count": 1,
                    "received_at": now,
                    "last_seen_at": now,
                },
            )
        try:
            command.downgrade(config, "c5a8e2f4b901")
        except Exception as exc:
            assert "Refusing to drop" in str(exc)
        else:
            raise AssertionError("Downgrade must refuse to erase new receipt provenance")

        print(
            "INTAKE_RECEIPT_MIGRATION_OK "
            f"receipts={receipt_count} items={item_count} shared_items={shared_count}"
        )
    finally:
        engine.dispose()
        Path(database_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
