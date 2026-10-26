"""Per-user ChatGPT plan connections (Sign in with ChatGPT) and their pending OAuth attempts."""

import sqlalchemy as sa
from alembic import op

revision = "7d9f1b3c5e68"
down_revision = "6c8e0a2b4d57"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_plan_connections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("issuer", sa.String(200), nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("client_id", sa.String(200), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("model", sa.String(200), nullable=True),
        sa.Column("models_json", sa.JSON(), nullable=False),
        sa.Column("use_by_default", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("encrypted_tokens", sa.Text(), nullable=True),
        sa.Column("access_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("earliest_refresh_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(80), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "provider", name="uq_ai_plan_connection_user"),
        sa.CheckConstraint(
            "status IN ('active', 'signed_out', 'reauth_required', 'plan_disabled')",
            name="ck_ai_plan_connection_status",
        ),
    )
    op.create_index("ix_ai_plan_connections_user_id", "ai_plan_connections", ["user_id"])
    op.create_table(
        "ai_plan_auth_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("state_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("client_id", sa.String(200), nullable=False),
        sa.Column("redirect_uri", sa.String(500), nullable=False),
        sa.Column("encrypted_secret", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ai_plan_auth_attempts_user_id", "ai_plan_auth_attempts", ["user_id"])
    op.create_index("ix_ai_plan_auth_attempts_expires_at", "ai_plan_auth_attempts", ["expires_at"])
    with op.batch_alter_table("document_graph_workspaces") as batch:
        batch.add_column(sa.Column("requested_by", sa.String(120), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("document_graph_workspaces") as batch:
        batch.drop_column("requested_by")
    op.drop_index("ix_ai_plan_auth_attempts_expires_at", table_name="ai_plan_auth_attempts")
    op.drop_index("ix_ai_plan_auth_attempts_user_id", table_name="ai_plan_auth_attempts")
    op.drop_table("ai_plan_auth_attempts")
    op.drop_index("ix_ai_plan_connections_user_id", table_name="ai_plan_connections")
    op.drop_table("ai_plan_connections")
