"""Track chat credential source without storing personal secrets."""

import sqlalchemy as sa
from alembic import op

revision = "3e5f7a9b1c24"
down_revision = "2d4e6f8a0b13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("chat_sessions") as batch:
        batch.add_column(
            sa.Column("credential_source", sa.String(20), nullable=False, server_default="system")
        )
        batch.create_check_constraint(
            "ck_chat_credential_source", "credential_source IN ('system', 'personal')"
        )


def downgrade() -> None:
    with op.batch_alter_table("chat_sessions") as batch:
        batch.drop_constraint("ck_chat_credential_source", type_="check")
        batch.drop_column("credential_source")
