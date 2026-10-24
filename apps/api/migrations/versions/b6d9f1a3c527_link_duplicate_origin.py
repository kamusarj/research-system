"""Record which submission a duplicate repeats.

A duplicate previously copied the original's ``research_id`` and kept nothing else. When
the original had not been approved yet that field was null, leaving the duplicate with no
research record, no way back into review, and no pointer to what it duplicated.

The whole change runs inside ``batch_alter_table``: SQLite cannot ALTER a constraint, and
this repository builds its schema on SQLite as well as PostgreSQL.

Revision ID: b6d9f1a3c527
Revises: a8b4c6d2e913
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b6d9f1a3c527"
down_revision: str | None = "a8b4c6d2e913"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("link_submissions") as batch:
        batch.add_column(sa.Column("duplicate_of_id", sa.String(length=36), nullable=True))
        batch.create_index("ix_link_submissions_duplicate_of_id", ["duplicate_of_id"])
        batch.create_foreign_key(
            "fk_link_submissions_duplicate_of_id",
            "link_submissions",
            ["duplicate_of_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("link_submissions") as batch:
        batch.drop_constraint("fk_link_submissions_duplicate_of_id", type_="foreignkey")
        batch.drop_index("ix_link_submissions_duplicate_of_id")
        batch.drop_column("duplicate_of_id")
