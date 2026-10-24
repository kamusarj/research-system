"""add graph chat sessions and messages

Revision ID: e9f5c2a7d104
Revises: d7e3b9a1f604
Create Date: 2026-07-18 12:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e9f5c2a7d104"
down_revision: str | None = "d7e3b9a1f604"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("scope_type", sa.String(30), nullable=False),
        sa.Column("scope_id", sa.String(36)),
        sa.Column("provider_name", sa.String(50), nullable=False),
        sa.Column("model_name", sa.String(200), nullable=False),
        sa.Column("conversation_summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("prompt_version", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(True), nullable=False),
        sa.Column("updated_at", sa.DateTime(True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_sessions_scope_type", "chat_sessions", ["scope_type"])
    op.create_index("ix_chat_sessions_scope_id", "chat_sessions", ["scope_id"])
    op.create_index("ix_chat_sessions_provider_name", "chat_sessions", ["provider_name"])
    op.create_index("ix_chat_sessions_status", "chat_sessions", ["status"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("provider_response_id", sa.String(200)),
        sa.Column("provider_request_id", sa.String(200)),
        sa.Column("tool_calls_json", sa.JSON(), nullable=False),
        sa.Column("tool_results_json", sa.JSON(), nullable=False),
        sa.Column("linked_change_set_id", sa.String(36)),
        sa.Column("usage_json", sa.JSON(), nullable=False),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("error_code", sa.String(80)),
        sa.Column("created_at", sa.DateTime(True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["linked_change_set_id"], ["graph_change_sets.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_index("ix_chat_messages_role", "chat_messages", ["role"])
    op.create_index(
        "ix_chat_messages_provider_response_id", "chat_messages", ["provider_response_id"]
    )
    op.create_index(
        "ix_chat_messages_linked_change_set_id", "chat_messages", ["linked_change_set_id"]
    )
    op.create_index("ix_chat_messages_error_code", "chat_messages", ["error_code"])


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
