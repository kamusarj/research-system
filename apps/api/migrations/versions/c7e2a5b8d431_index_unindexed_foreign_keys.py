"""Index the foreign keys that had none.

Five foreign keys had no supporting index, so every join or parent delete through them
scanned the whole child table. ``research_tags`` is the one that already hurt: its primary
key is ``(research_id, tag_id)``, and a composite index only serves lookups that start with
its leading column. Searching or listing related research goes the other way — from a tag
to its research items — and had nothing to use.

Revision ID: c7e2a5b8d431
Revises: b6d9f1a3c527
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c7e2a5b8d431"
down_revision: str | None = "b6d9f1a3c527"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (index name, table, column)
MISSING_FOREIGN_KEY_INDEXES: tuple[tuple[str, str, str], ...] = (
    ("ix_research_tags_tag_id", "research_tags", "tag_id"),
    ("ix_training_examples_event_id", "training_examples", "event_id"),
    ("ix_training_dataset_examples_example_id", "training_dataset_examples", "example_id"),
    ("ix_model_eval_runs_dataset_id", "model_eval_runs", "dataset_id"),
    ("ix_discovered_items_research_id", "discovered_items", "research_id"),
)


def upgrade() -> None:
    for name, table, column in MISSING_FOREIGN_KEY_INDEXES:
        op.create_index(name, table, [column])


def downgrade() -> None:
    for name, table, _column in reversed(MISSING_FOREIGN_KEY_INDEXES):
        op.drop_index(name, table_name=table)
