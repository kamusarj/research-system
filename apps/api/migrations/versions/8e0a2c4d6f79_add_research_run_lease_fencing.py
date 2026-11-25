"""Fence research workers with an immutable token for each claim."""

import sqlalchemy as sa
from alembic import op

revision = "8e0a2c4d6f79"
down_revision = "7d9f1b3c5e68"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("research_runs", sa.Column("lease_token", sa.String(36), nullable=True))
    op.create_index("ix_research_runs_lease_token", "research_runs", ["lease_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_research_runs_lease_token", table_name="research_runs")
    with op.batch_alter_table("research_runs") as batch:
        batch.drop_column("lease_token")
