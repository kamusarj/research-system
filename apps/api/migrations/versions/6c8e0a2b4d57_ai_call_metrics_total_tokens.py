"""Record total tokens for providers that do not split input and output (Codex CLI)."""

import sqlalchemy as sa
from alembic import op

revision = "6c8e0a2b4d57"
down_revision = "5b7d9f1c3e46"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ai_call_metrics") as batch:
        batch.add_column(sa.Column("total_tokens", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("ai_call_metrics") as batch:
        batch.drop_column("total_tokens")
