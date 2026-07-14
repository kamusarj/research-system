"""add link intake

Revision ID: 9f3c2a7b1d44
Revises: 5d7a8c91e2f0
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "9f3c2a7b1d44"
down_revision: Union[str, None] = "5d7a8c91e2f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "link_submissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("url", sa.String(length=2000), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_ref", sa.String(length=500), nullable=True),
        sa.Column("submitted_by", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("extracted_markdown", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("classification", sa.JSON(), nullable=False),
        sa.Column("provider_name", sa.String(length=80), nullable=True),
        sa.Column("model_name", sa.String(length=200), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("research_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["research_id"], ["research_items.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_link_submissions_url", "link_submissions", ["url"], unique=True)
    op.create_index(
        "ix_link_submissions_source_type", "link_submissions", ["source_type"], unique=False
    )
    op.create_index(
        "ix_link_submissions_source_ref", "link_submissions", ["source_ref"], unique=False
    )
    op.create_index("ix_link_submissions_status", "link_submissions", ["status"], unique=False)
    op.create_index(
        "ix_link_submissions_content_hash", "link_submissions", ["content_hash"], unique=False
    )
    op.create_index(
        "ix_link_submissions_research_id", "link_submissions", ["research_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_link_submissions_research_id", table_name="link_submissions")
    op.drop_index("ix_link_submissions_content_hash", table_name="link_submissions")
    op.drop_index("ix_link_submissions_status", table_name="link_submissions")
    op.drop_index("ix_link_submissions_source_ref", table_name="link_submissions")
    op.drop_index("ix_link_submissions_source_type", table_name="link_submissions")
    op.drop_index("ix_link_submissions_url", table_name="link_submissions")
    op.drop_table("link_submissions")
