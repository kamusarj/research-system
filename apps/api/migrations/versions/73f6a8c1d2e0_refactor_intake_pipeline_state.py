"""refactor intake pipeline state

Revision ID: 73f6a8c1d2e0
Revises: 4a6e8b2c9d10
Create Date: 2026-07-15 16:45:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "73f6a8c1d2e0"
down_revision: str | None = "4a6e8b2c9d10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("link_submissions") as batch:
        batch.add_column(
            sa.Column("stage", sa.String(length=40), nullable=False, server_default="pending")
        )
        batch.add_column(
            sa.Column(
                "review_status",
                sa.String(length=40),
                nullable=False,
                server_default="not_requested",
            )
        )
        batch.add_column(sa.Column("error_code", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("error_details", sa.JSON(), nullable=False, server_default="{}"))
        batch.create_index("ix_link_submissions_stage", ["stage"], unique=False)
        batch.create_index("ix_link_submissions_review_status", ["review_status"], unique=False)
        batch.create_index("ix_link_submissions_error_code", ["error_code"], unique=False)

    op.execute(
        """
        UPDATE link_submissions
        SET review_status = CASE
            WHEN status IN ('needs-review', 'classified') THEN 'needs_review'
            WHEN status = 'approved' THEN 'approved'
            WHEN status = 'rejected' THEN 'rejected'
            WHEN status = 'duplicate' THEN 'duplicate'
            ELSE 'not_requested'
        END,
        stage = CASE
            WHEN status IN ('queued', 'retrying') THEN 'pending'
            WHEN status = 'extracting' THEN 'extracting'
            ELSE 'completed'
        END,
        status = CASE
            WHEN status IN ('queued', 'retrying') THEN 'pending'
            WHEN status = 'extracting' THEN 'processing'
            WHEN status IN ('needs-transcript', 'needs-text-layer') THEN 'partial_success'
            WHEN status IN ('failed', 'dead-letter') THEN 'failed'
            ELSE 'completed'
        END
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE link_submissions
        SET status = CASE
            WHEN status = 'pending' THEN 'queued'
            WHEN status IN ('processing', 'fetching', 'extracting', 'analyzing')
                THEN 'extracting'
            WHEN status = 'partial_success' THEN 'needs-text-layer'
            WHEN status = 'failed' THEN 'dead-letter'
            WHEN review_status = 'needs_review' THEN 'needs-review'
            WHEN review_status = 'approved' THEN 'approved'
            WHEN review_status = 'rejected' THEN 'rejected'
            WHEN review_status = 'duplicate' THEN 'duplicate'
            ELSE 'needs-review'
        END
        """
    )
    with op.batch_alter_table("link_submissions") as batch:
        batch.drop_index("ix_link_submissions_error_code")
        batch.drop_index("ix_link_submissions_review_status")
        batch.drop_index("ix_link_submissions_stage")
        batch.drop_column("error_details")
        batch.drop_column("error_code")
        batch.drop_column("review_status")
        batch.drop_column("stage")
