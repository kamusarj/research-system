"""add ChatGPT shared snapshot import provenance

Revision ID: f6a2c9d4e801
Revises: e1f7a9c3b205
Create Date: 2026-08-01 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f6a2c9d4e801"
down_revision: str | None = "e1f7a9c3b205"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column("source_type", sa.String(length=30), server_default="local", nullable=False),
    )
    op.add_column(
        "chat_sessions", sa.Column("source_url", sa.String(length=2000), nullable=True)
    )
    op.add_column(
        "chat_sessions",
        sa.Column("source_snapshot_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "chat_sessions", sa.Column("source_imported_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "chat_sessions",
        sa.Column("imported_message_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "chat_messages",
        sa.Column("origin_type", sa.String(length=30), server_default="local", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "origin_type")
    op.drop_column("chat_sessions", "imported_message_count")
    op.drop_column("chat_sessions", "source_imported_at")
    op.drop_column("chat_sessions", "source_snapshot_hash")
    op.drop_column("chat_sessions", "source_url")
    op.drop_column("chat_sessions", "source_type")

