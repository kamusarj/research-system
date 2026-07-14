"""add knowledge gaps

Revision ID: 5d7a8c91e2f0
Revises: b4519e47487f
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "5d7a8c91e2f0"
down_revision: Union[str, None] = "b4519e47487f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_gaps",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=240), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("concept_key", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("coverage_count", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("assigned_to", sa.String(length=200), nullable=True),
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deep_research_id", sa.String(length=36), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["deep_research_id"], ["research_items.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_gaps_key", "knowledge_gaps", ["key"], unique=True)
    op.create_index(
        "ix_knowledge_gaps_concept_key", "knowledge_gaps", ["concept_key"], unique=False
    )
    op.create_index("ix_knowledge_gaps_status", "knowledge_gaps", ["status"], unique=False)
    op.create_index(
        "ix_knowledge_gaps_priority", "knowledge_gaps", ["priority"], unique=False
    )
    op.create_index(
        "ix_knowledge_gaps_deep_research_id",
        "knowledge_gaps",
        ["deep_research_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_gaps_deep_research_id", table_name="knowledge_gaps")
    op.drop_index("ix_knowledge_gaps_priority", table_name="knowledge_gaps")
    op.drop_index("ix_knowledge_gaps_status", table_name="knowledge_gaps")
    op.drop_index("ix_knowledge_gaps_concept_key", table_name="knowledge_gaps")
    op.drop_index("ix_knowledge_gaps_key", table_name="knowledge_gaps")
    op.drop_table("knowledge_gaps")
