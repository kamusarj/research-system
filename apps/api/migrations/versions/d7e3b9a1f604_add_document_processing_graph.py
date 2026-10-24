"""add document processing lifecycle and isolated graph

Revision ID: d7e3b9a1f604
Revises: a4f1c7d9e205
Create Date: 2026-07-18 11:05:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d7e3b9a1f604"
down_revision: str | None = "a4f1c7d9e205"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("document_graph_workspaces", sa.Column("provider_name", sa.String(80)))
    op.add_column("document_graph_workspaces", sa.Column("model_name", sa.String(200)))
    op.add_column(
        "document_graph_workspaces",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("document_graph_workspaces", sa.Column("next_attempt_at", sa.DateTime(True)))
    op.add_column("document_graph_workspaces", sa.Column("started_at", sa.DateTime(True)))
    op.add_column("document_graph_workspaces", sa.Column("finished_at", sa.DateTime(True)))
    op.add_column(
        "document_graph_workspaces",
        sa.Column("extracted_char_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_document_graph_workspaces_next_attempt_at",
        "document_graph_workspaces",
        ["next_attempt_at"],
    )

    op.create_table(
        "document_graph_nodes",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("local_key", sa.String(80), nullable=False),
        sa.Column("node_type", sa.String(40), nullable=False),
        sa.Column("label", sa.String(250), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("parent_node_id", sa.String(36)),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_status", sa.String(30), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(True), nullable=False),
        sa.Column("updated_at", sa.DateTime(True), nullable=False),
        sa.CheckConstraint("parent_node_id IS NULL OR parent_node_id <> id", name="ck_document_node_parent"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_document_node_confidence"),
        sa.ForeignKeyConstraint(["parent_node_id"], ["document_graph_nodes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["document_graph_workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "local_key", name="uq_document_node_local_key"),
    )
    op.create_index("ix_document_graph_nodes_workspace_id", "document_graph_nodes", ["workspace_id"])
    op.create_index("ix_document_graph_nodes_node_type", "document_graph_nodes", ["node_type"])
    op.create_index("ix_document_graph_nodes_parent_node_id", "document_graph_nodes", ["parent_node_id"])
    op.create_index("ix_document_graph_nodes_evidence_status", "document_graph_nodes", ["evidence_status"])

    op.create_table(
        "document_graph_edges",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("source_node_id", sa.String(36), nullable=False),
        sa.Column("target_node_id", sa.String(36), nullable=False),
        sa.Column("edge_type", sa.String(60), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_status", sa.String(30), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(True), nullable=False),
        sa.Column("updated_at", sa.DateTime(True), nullable=False),
        sa.CheckConstraint("source_node_id <> target_node_id", name="ck_document_graph_edge_self_loop"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_document_edge_confidence"),
        sa.ForeignKeyConstraint(["source_node_id"], ["document_graph_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["document_graph_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["document_graph_workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "source_node_id", "target_node_id", "edge_type", name="uq_document_graph_edge"),
    )
    op.create_index("ix_document_graph_edges_workspace_id", "document_graph_edges", ["workspace_id"])
    op.create_index("ix_document_graph_edges_source_node_id", "document_graph_edges", ["source_node_id"])
    op.create_index("ix_document_graph_edges_target_node_id", "document_graph_edges", ["target_node_id"])
    op.create_index("ix_document_graph_edges_edge_type", "document_graph_edges", ["edge_type"])
    op.create_index("ix_document_graph_edges_evidence_status", "document_graph_edges", ["evidence_status"])


def downgrade() -> None:
    op.drop_table("document_graph_edges")
    op.drop_table("document_graph_nodes")
    op.drop_index("ix_document_graph_workspaces_next_attempt_at", table_name="document_graph_workspaces")
    op.drop_column("document_graph_workspaces", "extracted_char_count")
    op.drop_column("document_graph_workspaces", "finished_at")
    op.drop_column("document_graph_workspaces", "started_at")
    op.drop_column("document_graph_workspaces", "next_attempt_at")
    op.drop_column("document_graph_workspaces", "attempt_count")
    op.drop_column("document_graph_workspaces", "model_name")
    op.drop_column("document_graph_workspaces", "provider_name")
