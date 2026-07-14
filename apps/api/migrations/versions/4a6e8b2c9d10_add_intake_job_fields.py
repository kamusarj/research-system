"""add intake job fields

Revision ID: 4a6e8b2c9d10
Revises: 9f3c2a7b1d44
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "4a6e8b2c9d10"
down_revision: Union[str, None] = "9f3c2a7b1d44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "link_submissions",
        sa.Column("auto_approve", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "link_submissions",
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "link_submissions",
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "link_submissions", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "link_submissions", sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index(
        "ix_link_submissions_next_attempt_at",
        "link_submissions",
        ["next_attempt_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_link_submissions_next_attempt_at", table_name="link_submissions")
    op.drop_column("link_submissions", "finished_at")
    op.drop_column("link_submissions", "started_at")
    op.drop_column("link_submissions", "next_attempt_at")
    op.drop_column("link_submissions", "attempt_count")
    op.drop_column("link_submissions", "auto_approve")
