"""add bounded chat message media metadata

Revision ID: f8b3d1e6a204
Revises: f6a2c9d4e801
Create Date: 2026-08-01 23:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f8b3d1e6a204"
down_revision: str | None = "f6a2c9d4e801"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chat_messages",
        sa.Column("media_json", sa.JSON(), server_default="[]", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "media_json")
