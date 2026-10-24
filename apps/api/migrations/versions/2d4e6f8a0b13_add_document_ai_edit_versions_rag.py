"""add document source versions, ai edits and rag status

Revision ID: 2d4e6f8a0b13
Revises: f8b3d1e6a204
Create Date: 2026-08-02 20:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2d4e6f8a0b13"
down_revision: str | None = "f8b3d1e6a204"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("document_graph_workspaces") as batch:
        batch.add_column(
            sa.Column("source_version", sa.Integer(), nullable=False, server_default="1")
        )
        batch.add_column(
            sa.Column("rag_status", sa.String(length=30), nullable=False, server_default="pending")
        )
        batch.add_column(
            sa.Column("rag_chunk_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(sa.Column("rag_indexed_version", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("rag_error_code", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("rag_indexed_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_document_graph_workspaces_rag_status", ["rag_status"])
        batch.create_index("ix_document_graph_workspaces_rag_error_code", ["rag_error_code"])

    op.create_table(
        "document_source_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("object_key", sa.String(length=1000), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("origin", sa.String(length=30), nullable=False),
        sa.Column("change_summary", sa.String(length=500), nullable=True),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("size_bytes >= 0", name="ck_document_source_version_size"),
        sa.CheckConstraint(
            "version_number >= 1", name="ck_document_source_version_positive"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["document_graph_workspaces.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id", "version_number", name="uq_document_source_version_number"
        ),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index(
        "ix_document_source_versions_workspace_id",
        "document_source_versions",
        ["workspace_id"],
    )
    op.create_index(
        "ix_document_source_versions_content_hash",
        "document_source_versions",
        ["content_hash"],
    )
    op.create_index(
        "ix_document_source_versions_origin", "document_source_versions", ["origin"]
    )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            INSERT INTO document_source_versions
                (id, workspace_id, version_number, object_key, content_hash,
                 size_bytes, origin, change_summary, created_by, created_at)
            SELECT w.id, w.id, 1, w.storage_object_key, w.content_hash,
                   a.size_bytes, 'upload', 'Initial uploaded source', 'migration', w.created_at
            FROM document_graph_workspaces w
            JOIN attachments a ON a.id = w.attachment_id
            """
        )
    )

    op.create_table(
        "document_ai_edit_proposals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("base_version_number", sa.Integer(), nullable=False),
        sa.Column("selection_start", sa.Integer(), nullable=False),
        sa.Column("selection_end", sa.Integer(), nullable=False),
        sa.Column("selected_text_hash", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("instruction", sa.String(length=1000), nullable=True),
        sa.Column("replacement_text", sa.Text(), nullable=False),
        sa.Column("explanation", sa.String(length=1000), nullable=False),
        sa.Column("provider_name", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=False),
        sa.Column("prompt_version", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("accepted_version_number", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("reviewed_by", sa.String(length=120), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("selection_start >= 0", name="ck_document_ai_edit_start"),
        sa.CheckConstraint(
            "selection_end > selection_start", name="ck_document_ai_edit_range"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["document_graph_workspaces.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_ai_edit_proposals_workspace_id",
        "document_ai_edit_proposals",
        ["workspace_id"],
    )
    op.create_index(
        "ix_document_ai_edit_proposals_status",
        "document_ai_edit_proposals",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_ai_edit_proposals_status", table_name="document_ai_edit_proposals"
    )
    op.drop_index(
        "ix_document_ai_edit_proposals_workspace_id",
        table_name="document_ai_edit_proposals",
    )
    op.drop_table("document_ai_edit_proposals")
    op.drop_index("ix_document_source_versions_origin", table_name="document_source_versions")
    op.drop_index(
        "ix_document_source_versions_content_hash", table_name="document_source_versions"
    )
    op.drop_index(
        "ix_document_source_versions_workspace_id", table_name="document_source_versions"
    )
    op.drop_table("document_source_versions")
    with op.batch_alter_table("document_graph_workspaces") as batch:
        batch.drop_index("ix_document_graph_workspaces_rag_error_code")
        batch.drop_index("ix_document_graph_workspaces_rag_status")
        batch.drop_column("rag_indexed_at")
        batch.drop_column("rag_error_code")
        batch.drop_column("rag_indexed_version")
        batch.drop_column("rag_chunk_count")
        batch.drop_column("rag_status")
        batch.drop_column("source_version")
