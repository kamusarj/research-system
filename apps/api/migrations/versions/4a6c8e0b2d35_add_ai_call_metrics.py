"""Record latency and token usage per AI provider call (no prompt or output content)."""

import sqlalchemy as sa
from alembic import op

revision = "4a6c8e0b2d35"
down_revision = "3e5f7a9b1c24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_call_metrics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("operation", sa.String(80), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cached_input_tokens", sa.Integer(), nullable=True),
        sa.Column("prompt_chars", sa.Integer(), nullable=True),
        sa.Column("cache_hit", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_call_metrics_operation", "ai_call_metrics", ["operation"])
    op.create_index("ix_ai_call_metrics_created_at", "ai_call_metrics", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_call_metrics_created_at", table_name="ai_call_metrics")
    op.drop_index("ix_ai_call_metrics_operation", table_name="ai_call_metrics")
    op.drop_table("ai_call_metrics")
