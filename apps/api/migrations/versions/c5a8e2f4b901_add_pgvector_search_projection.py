"""add pgvector search projection

Revision ID: c5a8e2f4b901
Revises: 0b7d2e4f6a18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "c5a8e2f4b901"
down_revision: str | None = "0b7d2e4f6a18"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    embedding_type = Vector(1024) if dialect == "postgresql" else sa.JSON()
    op.create_table(
        "search_vector_projections",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("research_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding", embedding_type, nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sync_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["research_id"], ["research_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("research_id", "chunk_index"),
    )
    op.create_index(
        op.f("ix_search_vector_projections_research_id"),
        "search_vector_projections",
        ["research_id"],
    )
    op.create_index(
        op.f("ix_search_vector_projections_content_hash"),
        "search_vector_projections",
        ["content_hash"],
    )
    op.create_index(
        op.f("ix_search_vector_projections_sync_id"),
        "search_vector_projections",
        ["sync_id"],
    )
    op.create_index(
        "ix_search_vector_projections_embedding_hnsw",
        "search_vector_projections",
        ["embedding"],
        postgresql_using="hnsw" if dialect == "postgresql" else None,
        postgresql_ops={"embedding": "vector_cosine_ops"} if dialect == "postgresql" else None,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_search_vector_projections_embedding_hnsw",
        table_name="search_vector_projections",
    )
    op.drop_index(
        op.f("ix_search_vector_projections_sync_id"),
        table_name="search_vector_projections",
    )
    op.drop_index(
        op.f("ix_search_vector_projections_content_hash"),
        table_name="search_vector_projections",
    )
    op.drop_index(
        op.f("ix_search_vector_projections_research_id"),
        table_name="search_vector_projections",
    )
    op.drop_table("search_vector_projections")
