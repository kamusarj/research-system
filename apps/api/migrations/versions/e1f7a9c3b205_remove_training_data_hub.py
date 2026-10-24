"""Remove the retired Training Data Hub schema.

The owner explicitly retired the Training Data product domain. Existing rows
are deleted with these tables; downgrade recreates only the empty schema.

Revision ID: e1f7a9c3b205
Revises: d8f3b1c6a247
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e1f7a9c3b205"
down_revision: str | None = "d8f3b1c6a247"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("training_dataset_examples")
    op.drop_table("model_eval_runs")
    op.drop_table("training_examples")
    op.drop_table("preference_pairs")
    op.drop_table("training_events")
    op.drop_table("training_datasets")


def downgrade() -> None:
    op.create_table(
        "training_datasets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "version"),
    )
    op.create_table(
        "training_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_training_events_event_type"),
        "training_events",
        ["event_type"],
        unique=False,
    )
    op.create_table(
        "preference_pairs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("chosen", sa.Text(), nullable=False),
        sa.Column("rejected", sa.Text(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "training_examples",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=True),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column("expected_response", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("split", sa.String(length=20), nullable=False),
        sa.Column("pii_status", sa.String(length=30), nullable=False),
        sa.Column("policy_status", sa.String(length=30), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["training_events.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_training_examples_status"),
        "training_examples",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_training_examples_event_id",
        "training_examples",
        ["event_id"],
        unique=False,
    )
    op.create_table(
        "model_eval_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["training_datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_model_eval_runs_dataset_id",
        "model_eval_runs",
        ["dataset_id"],
        unique=False,
    )
    op.create_table(
        "training_dataset_examples",
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("example_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["training_datasets.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["example_id"],
            ["training_examples.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("dataset_id", "example_id"),
    )
    op.create_index(
        "ix_training_dataset_examples_example_id",
        "training_dataset_examples",
        ["example_id"],
        unique=False,
    )
