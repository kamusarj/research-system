"""add source-neutral intake receipts and service accounts

Revision ID: a8b4c6d2e913
Revises: c5a8e2f4b901
"""

import hashlib
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "a8b4c6d2e913"
down_revision: str | None = "c5a8e2f4b901"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BACKFILL_NAMESPACE = uuid.UUID("6d76ab93-f9ba-4ccb-a88b-acde4f27b628")


def _hash(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode()).hexdigest()


def _timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    return datetime.now(UTC)


def upgrade() -> None:
    op.create_table(
        "service_accounts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("source_namespace", sa.String(length=120), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_prefix", sa.String(length=20), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_service_accounts_source_namespace", "service_accounts", ["source_namespace"])
    op.create_index("ix_service_accounts_token_hash", "service_accounts", ["token_hash"], unique=True)
    op.create_index("ix_service_accounts_active", "service_accounts", ["active"])
    op.create_index("ix_service_accounts_expires_at", "service_accounts", ["expires_at"])
    op.create_index("ix_service_accounts_revoked_at", "service_accounts", ["revoked_at"])

    op.create_table(
        "intake_receipts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_namespace", sa.String(length=120), nullable=False),
        sa.Column("external_occurrence_ref", sa.String(length=500), nullable=False),
        sa.Column("delivery_key_hash", sa.String(length=64), nullable=False),
        sa.Column("container_ref", sa.String(length=200), nullable=True),
        sa.Column("submitted_by", sa.String(length=200), nullable=False),
        sa.Column("external_actor_ref_hash", sa.String(length=64), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("delivery_count", sa.Integer(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source_type IN ('manual', 'api', 'discord')", name="ck_intake_receipt_source_type"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_intake_receipts_source_type", "intake_receipts", ["source_type"])
    op.create_index(
        "ix_intake_receipts_source_namespace", "intake_receipts", ["source_namespace"]
    )
    op.create_index(
        "ix_intake_receipts_delivery_key_hash",
        "intake_receipts",
        ["delivery_key_hash"],
        unique=True,
    )
    op.create_index("ix_intake_receipts_submitted_by", "intake_receipts", ["submitted_by"])

    op.create_table(
        "intake_receipt_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("receipt_id", sa.String(length=36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("item_key_hash", sa.String(length=64), nullable=False),
        sa.Column("normalized_url", sa.String(length=2000), nullable=True),
        sa.Column("external_item_ref", sa.String(length=500), nullable=True),
        sa.Column("content_sha256", sa.String(length=64), nullable=True),
        sa.Column("link_submission_id", sa.String(length=36), nullable=True),
        sa.Column("document_workspace_id", sa.String(length=36), nullable=True),
        sa.Column("initial_disposition", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('url', 'document')", name="ck_intake_receipt_item_kind"),
        sa.CheckConstraint(
            "initial_disposition IN ('queued', 'linked_existing')",
            name="ck_intake_receipt_item_disposition",
        ),
        sa.CheckConstraint(
            "((link_submission_id IS NOT NULL AND document_workspace_id IS NULL) OR "
            "(link_submission_id IS NULL AND document_workspace_id IS NOT NULL))",
            name="ck_intake_receipt_item_one_target",
        ),
        sa.ForeignKeyConstraint(["receipt_id"], ["intake_receipts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["link_submission_id"], ["link_submissions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["document_workspace_id"], ["document_graph_workspaces.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("receipt_id", "ordinal", name="uq_intake_receipt_item_ordinal"),
        sa.UniqueConstraint("receipt_id", "item_key_hash", name="uq_intake_receipt_item_key"),
        sa.UniqueConstraint(
            "receipt_id",
            "kind",
            "external_item_ref",
            name="uq_intake_receipt_document_ref",
        ),
    )
    op.create_index("ix_intake_receipt_items_receipt_id", "intake_receipt_items", ["receipt_id"])
    op.create_index("ix_intake_receipt_items_kind", "intake_receipt_items", ["kind"])
    op.create_index(
        "ix_intake_receipt_items_link_submission_id",
        "intake_receipt_items",
        ["link_submission_id"],
    )
    op.create_index(
        "ix_intake_receipt_items_document_workspace_id",
        "intake_receipt_items",
        ["document_workspace_id"],
    )

    connection = op.get_bind()
    submissions = sa.table(
        "link_submissions",
        sa.column("id", sa.String()),
        sa.column("url", sa.String()),
        sa.column("source_type", sa.String()),
        sa.column("source_ref", sa.String()),
        sa.column("submitted_by", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    rows = list(
        connection.execute(
            sa.select(
                submissions.c.id,
                submissions.c.url,
                submissions.c.source_type,
                submissions.c.source_ref,
                submissions.c.submitted_by,
                submissions.c.created_at,
            ).order_by(submissions.c.created_at, submissions.c.id)
        ).mappings()
    )
    receipt_table = sa.table(
        "intake_receipts",
        sa.column("id", sa.String()),
        sa.column("source_type", sa.String()),
        sa.column("source_namespace", sa.String()),
        sa.column("external_occurrence_ref", sa.String()),
        sa.column("delivery_key_hash", sa.String()),
        sa.column("container_ref", sa.String()),
        sa.column("submitted_by", sa.String()),
        sa.column("external_actor_ref_hash", sa.String()),
        sa.column("metadata", sa.JSON()),
        sa.column("delivery_count", sa.Integer()),
        sa.column("received_at", sa.DateTime(timezone=True)),
        sa.column("last_seen_at", sa.DateTime(timezone=True)),
    )
    item_table = sa.table(
        "intake_receipt_items",
        sa.column("id", sa.String()),
        sa.column("receipt_id", sa.String()),
        sa.column("ordinal", sa.Integer()),
        sa.column("kind", sa.String()),
        sa.column("item_key_hash", sa.String()),
        sa.column("normalized_url", sa.String()),
        sa.column("external_item_ref", sa.String()),
        sa.column("content_sha256", sa.String()),
        sa.column("link_submission_id", sa.String()),
        sa.column("document_workspace_id", sa.String()),
        sa.column("initial_disposition", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    grouped: dict[tuple[str, str], list[sa.RowMapping]] = {}
    for row in rows:
        source_type = row["source_type"] if row["source_type"] in {"manual", "api", "discord"} else "api"
        occurrence_ref = row["source_ref"] or row["id"]
        group_key = (source_type, occurrence_ref) if row["source_ref"] else (source_type, row["id"])
        grouped.setdefault(group_key, []).append(row)

    receipt_rows: list[dict[str, object]] = []
    item_rows: list[dict[str, object]] = []
    for (source_type, occurrence_ref), group in grouped.items():
        identity = f"{source_type}\0legacy\0{occurrence_ref}"
        receipt_id = str(uuid.uuid5(_BACKFILL_NAMESPACE, f"receipt\0{identity}"))
        first_seen = _timestamp(group[0]["created_at"])
        last_seen = max(_timestamp(row["created_at"]) for row in group)
        receipt_rows.append(
            {
                "id": receipt_id,
                "source_type": source_type,
                "source_namespace": "legacy",
                "external_occurrence_ref": occurrence_ref,
                "delivery_key_hash": _hash("receipt-v1", source_type, "legacy", occurrence_ref),
                "container_ref": None,
                "submitted_by": group[0]["submitted_by"] or "local-user",
                "external_actor_ref_hash": None,
                "metadata": {"schema_version": 1, "legacy_backfill": True},
                "delivery_count": 1,
                "received_at": first_seen,
                "last_seen_at": last_seen,
            }
        )
        for ordinal, row in enumerate(group, start=1):
            item_rows.append(
                {
                    "id": str(
                        uuid.uuid5(_BACKFILL_NAMESPACE, f"item\0{receipt_id}\0{row['id']}")
                    ),
                    "receipt_id": receipt_id,
                    "ordinal": ordinal,
                    "kind": "url",
                    "item_key_hash": _hash("url-v1", row["url"]),
                    "normalized_url": row["url"],
                    "external_item_ref": None,
                    "content_sha256": None,
                    "link_submission_id": row["id"],
                    "document_workspace_id": None,
                    "initial_disposition": "linked_existing",
                    "created_at": _timestamp(row["created_at"]),
                }
            )
    if receipt_rows:
        op.bulk_insert(receipt_table, receipt_rows)
        op.bulk_insert(item_table, item_rows)


def downgrade() -> None:
    connection = op.get_bind()
    service_count = int(
        connection.scalar(sa.text("SELECT COUNT(*) FROM service_accounts")) or 0
    )
    new_receipt_count = int(
        connection.scalar(
            sa.text("SELECT COUNT(*) FROM intake_receipts WHERE source_namespace <> 'legacy'")
        )
        or 0
    )
    if service_count or new_receipt_count:
        raise RuntimeError(
            "Refusing to drop service accounts or non-legacy intake receipt provenance"
        )

    op.drop_index("ix_intake_receipt_items_document_workspace_id", table_name="intake_receipt_items")
    op.drop_index("ix_intake_receipt_items_link_submission_id", table_name="intake_receipt_items")
    op.drop_index("ix_intake_receipt_items_kind", table_name="intake_receipt_items")
    op.drop_index("ix_intake_receipt_items_receipt_id", table_name="intake_receipt_items")
    op.drop_table("intake_receipt_items")
    op.drop_index("ix_intake_receipts_submitted_by", table_name="intake_receipts")
    op.drop_index("ix_intake_receipts_delivery_key_hash", table_name="intake_receipts")
    op.drop_index("ix_intake_receipts_source_namespace", table_name="intake_receipts")
    op.drop_index("ix_intake_receipts_source_type", table_name="intake_receipts")
    op.drop_table("intake_receipts")
    op.drop_index("ix_service_accounts_revoked_at", table_name="service_accounts")
    op.drop_index("ix_service_accounts_expires_at", table_name="service_accounts")
    op.drop_index("ix_service_accounts_active", table_name="service_accounts")
    op.drop_index("ix_service_accounts_token_hash", table_name="service_accounts")
    op.drop_index("ix_service_accounts_source_namespace", table_name="service_accounts")
    op.drop_table("service_accounts")
