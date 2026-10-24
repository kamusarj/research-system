"""add source overrides to link submissions

Revision ID: 0b7d2e4f6a18
Revises: f3a6c8d1e204
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0b7d2e4f6a18"
down_revision: str | None = "f3a6c8d1e204"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("link_submissions") as batch:
        batch.add_column(
            sa.Column(
                "source_overrides",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("link_submissions") as batch:
        batch.drop_column("source_overrides")
