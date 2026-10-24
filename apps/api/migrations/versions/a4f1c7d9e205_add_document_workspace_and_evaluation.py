"""add document workspace and paper evaluation

Revision ID: a4f1c7d9e205
Revises: 8c2d4e6f901a
Create Date: 2026-07-18 10:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a4f1c7d9e205"
down_revision: str | None = "8c2d4e6f901a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_graph_workspaces",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("research_id", sa.String(length=36), nullable=False),
        sa.Column("attachment_id", sa.String(length=36), nullable=False),
        sa.Column("storage_object_key", sa.String(length=1000), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("processing_status", sa.String(length=40), nullable=False),
        sa.Column("review_status", sa.String(length=40), nullable=False),
        sa.Column("extraction_limitations", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["attachment_id"], ["attachments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["research_id"], ["research_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_object_key"),
    )
    op.create_index(
        "ix_document_graph_workspaces_research_id", "document_graph_workspaces", ["research_id"]
    )
    op.create_index(
        "ix_document_graph_workspaces_attachment_id",
        "document_graph_workspaces",
        ["attachment_id"],
        unique=True,
    )
    op.create_index(
        "ix_document_graph_workspaces_content_hash",
        "document_graph_workspaces",
        ["content_hash"],
        unique=True,
    )
    op.create_index(
        "ix_document_graph_workspaces_processing_status",
        "document_graph_workspaces",
        ["processing_status"],
    )
    op.create_index(
        "ix_document_graph_workspaces_review_status",
        "document_graph_workspaces",
        ["review_status"],
    )
    op.create_index(
        "ix_document_graph_workspaces_error_code", "document_graph_workspaces", ["error_code"]
    )

    op.create_table(
        "paper_evaluations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("rubric_version", sa.String(length=100), nullable=False),
        sa.Column("dimension_scores", sa.JSON(), nullable=False),
        sa.Column("fit_score", sa.Float(), nullable=True),
        sa.Column("decision", sa.String(length=40), nullable=False),
        sa.Column("failed_gates", sa.JSON(), nullable=False),
        sa.Column("matched_pillars", sa.JSON(), nullable=False),
        sa.Column("candidate_parents", sa.JSON(), nullable=False),
        sa.Column("contribution_types", sa.JSON(), nullable=False),
        sa.Column("overlaps_with", sa.JSON(), nullable=False),
        sa.Column("fills_gaps", sa.JSON(), nullable=False),
        sa.Column("limitations", sa.JSON(), nullable=False),
        sa.Column("reasoning_summary", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("provider_name", sa.String(length=80), nullable=True),
        sa.Column("model_name", sa.String(length=200), nullable=True),
        sa.Column("prompt_version", sa.String(length=100), nullable=True),
        sa.Column("input_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "fit_score IS NULL OR (fit_score >= 0 AND fit_score <= 100)",
            name="ck_paper_fit_score",
        ),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_paper_confidence"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["document_graph_workspaces.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_paper_evaluations_workspace_id", "paper_evaluations", ["workspace_id"], unique=True
    )
    op.create_index(
        "ix_paper_evaluations_rubric_version", "paper_evaluations", ["rubric_version"]
    )
    op.create_index("ix_paper_evaluations_decision", "paper_evaluations", ["decision"])
    op.create_index("ix_paper_evaluations_input_hash", "paper_evaluations", ["input_hash"])


def downgrade() -> None:
    op.drop_table("paper_evaluations")
    op.drop_table("document_graph_workspaces")
