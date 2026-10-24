"""add graph intelligence ontology

Revision ID: 8c2d4e6f901a
Revises: 73f6a8c1d2e0
Create Date: 2026-07-18 10:10:00
"""

from collections.abc import Sequence
from datetime import UTC, datetime
import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "8c2d4e6f901a"
down_revision: str | None = "73f6a8c1d2e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ONTOLOGY_NAMESPACE = uuid.UUID("83f8c449-6c7b-5cdd-92e7-88c6c2d97219")
ROOT_KEY = "business-ai-agents"
PILLARS = (
    ("business-problems-outcomes", "Business Problems & Outcomes", "Bài toán và kết quả kinh doanh"),
    ("business-context", "Business Context", "Bối cảnh kinh doanh"),
    ("agent-system-architecture", "Agent System Architecture", "Kiến trúc hệ thống agent"),
    ("agent-capabilities-workflows", "Agent Capabilities & Workflows", "Năng lực và quy trình agent"),
    (
        "business-methods-decision-intelligence",
        "Business Methods & Decision Intelligence",
        "Phương pháp kinh doanh và trí tuệ quyết định",
    ),
    ("data-knowledge-memory", "Data, Knowledge & Memory", "Dữ liệu, tri thức và bộ nhớ"),
    (
        "tools-functions-integrations",
        "Tools, Functions & Integrations",
        "Công cụ, hàm và tích hợp",
    ),
    ("outputs-actions-feedback", "Outputs, Actions & Feedback", "Đầu ra, hành động và phản hồi"),
    (
        "evaluation-risk-governance",
        "Evaluation, Risk & Governance",
        "Đánh giá, rủi ro và quản trị",
    ),
    ("engineering-operations", "Engineering & Operations", "Kỹ thuật và vận hành"),
    ("research-evidence", "Research & Evidence", "Nghiên cứu và bằng chứng"),
)


def ontology_id(key: str) -> str:
    return str(uuid.uuid5(ONTOLOGY_NAMESPACE, key))


def upgrade() -> None:
    op.create_table(
        "knowledge_nodes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("node_type", sa.String(length=60), nullable=False),
        sa.Column("canonical_label", sa.String(length=250), nullable=False),
        sa.Column("label_vi", sa.String(length=250), nullable=True),
        sa.Column("normalized_key", sa.String(length=250), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("scope_note", sa.Text(), nullable=True),
        sa.Column("primary_parent_id", sa.String(length=36), nullable=True),
        sa.Column("lifecycle_status", sa.String(length=30), nullable=False),
        sa.Column("created_by_type", sa.String(length=30), nullable=False),
        sa.Column("created_by_ref", sa.String(length=100), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("primary_parent_id IS NULL OR primary_parent_id <> id", name="ck_node_parent"),
        sa.ForeignKeyConstraint(["primary_parent_id"], ["knowledge_nodes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("node_type", "normalized_key", name="uq_knowledge_node_type_key"),
    )
    op.create_index("ix_knowledge_nodes_node_type", "knowledge_nodes", ["node_type"])
    op.create_index("ix_knowledge_nodes_normalized_key", "knowledge_nodes", ["normalized_key"])
    op.create_index("ix_knowledge_nodes_primary_parent_id", "knowledge_nodes", ["primary_parent_id"])
    op.create_index("ix_knowledge_nodes_lifecycle_status", "knowledge_nodes", ["lifecycle_status"])

    op.create_table(
        "knowledge_edges",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_node_id", sa.String(length=36), nullable=False),
        sa.Column("target_node_id", sa.String(length=36), nullable=False),
        sa.Column("edge_type", sa.String(length=60), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=30), nullable=False),
        sa.Column("evidence_status", sa.String(length=30), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_by_type", sa.String(length=30), nullable=False),
        sa.Column("created_by_ref", sa.String(length=100), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("source_node_id <> target_node_id", name="ck_knowledge_edge_self_loop"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_edge_confidence"),
        sa.ForeignKeyConstraint(["source_node_id"], ["knowledge_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["knowledge_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_node_id",
            "target_node_id",
            "edge_type",
            "lifecycle_status",
            name="uq_active_knowledge_edge",
        ),
    )
    op.create_index("ix_knowledge_edges_source_node_id", "knowledge_edges", ["source_node_id"])
    op.create_index("ix_knowledge_edges_target_node_id", "knowledge_edges", ["target_node_id"])
    op.create_index("ix_knowledge_edges_edge_type", "knowledge_edges", ["edge_type"])
    op.create_index("ix_knowledge_edges_lifecycle_status", "knowledge_edges", ["lifecycle_status"])

    op.create_table(
        "concept_aliases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("knowledge_node_id", sa.String(length=36), nullable=False),
        sa.Column("alias", sa.String(length=250), nullable=False),
        sa.Column("normalized_alias", sa.String(length=250), nullable=False),
        sa.Column("language", sa.String(length=12), nullable=False),
        sa.Column("alias_type", sa.String(length=30), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=30), nullable=False),
        sa.Column("created_by_type", sa.String(length=30), nullable=False),
        sa.Column("created_by_ref", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_node_id"], ["knowledge_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_alias", "language", name="uq_concept_alias_language"),
    )
    op.create_index("ix_concept_aliases_knowledge_node_id", "concept_aliases", ["knowledge_node_id"])
    op.create_index("ix_concept_aliases_normalized_alias", "concept_aliases", ["normalized_alias"])
    op.create_index("ix_concept_aliases_lifecycle_status", "concept_aliases", ["lifecycle_status"])

    op.create_table(
        "node_evidence",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_kind", sa.String(length=30), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("source_document_id", sa.String(length=36), nullable=True),
        sa.Column("location", sa.JSON(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("extraction_method", sa.String(length=60), nullable=True),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_document_id"], ["research_items.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_node_evidence_owner_kind", "node_evidence", ["owner_kind"])
    op.create_index("ix_node_evidence_owner_id", "node_evidence", ["owner_id"])
    op.create_index("ix_node_evidence_source_document_id", "node_evidence", ["source_document_id"])
    op.create_index("ix_node_evidence_content_hash", "node_evidence", ["content_hash"])

    op.create_table(
        "graph_change_sets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("origin_type", sa.String(length=30), nullable=False),
        sa.Column("origin_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=30), nullable=False),
        sa.Column("validation_summary", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("approved_by", sa.String(length=120), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_graph_change_sets_origin_type", "graph_change_sets", ["origin_type"])
    op.create_index("ix_graph_change_sets_origin_id", "graph_change_sets", ["origin_id"])
    op.create_index("ix_graph_change_sets_lifecycle_status", "graph_change_sets", ["lifecycle_status"])

    op.create_table(
        "graph_mutations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("change_set_id", sa.String(length=36), nullable=False),
        sa.Column("mutation_order", sa.Integer(), nullable=False),
        sa.Column("operation", sa.String(length=40), nullable=False),
        sa.Column("target_kind", sa.String(length=20), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=True),
        sa.Column("before_json", sa.JSON(), nullable=False),
        sa.Column("proposed_json", sa.JSON(), nullable=False),
        sa.Column("validation_status", sa.String(length=30), nullable=False),
        sa.Column("validation_messages", sa.JSON(), nullable=False),
        sa.Column("review_decision", sa.String(length=30), nullable=False),
        sa.Column("reviewed_by", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["change_set_id"], ["graph_change_sets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("change_set_id", "mutation_order"),
    )
    op.create_index("ix_graph_mutations_change_set_id", "graph_mutations", ["change_set_id"])
    op.create_index("ix_graph_mutations_operation", "graph_mutations", ["operation"])
    op.create_index("ix_graph_mutations_target_id", "graph_mutations", ["target_id"])
    op.create_index("ix_graph_mutations_validation_status", "graph_mutations", ["validation_status"])
    op.create_index("ix_graph_mutations_review_decision", "graph_mutations", ["review_decision"])

    now = datetime.now(UTC)
    root_id = ontology_id(ROOT_KEY)
    nodes = sa.table(
        "knowledge_nodes",
        sa.column("id", sa.String),
        sa.column("node_type", sa.String),
        sa.column("canonical_label", sa.String),
        sa.column("label_vi", sa.String),
        sa.column("normalized_key", sa.String),
        sa.column("description", sa.Text),
        sa.column("scope_note", sa.Text),
        sa.column("primary_parent_id", sa.String),
        sa.column("lifecycle_status", sa.String),
        sa.column("created_by_type", sa.String),
        sa.column("created_by_ref", sa.String),
        sa.column("metadata", sa.JSON),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    rows = [
        {
            "id": root_id,
            "node_type": "SystemRoot",
            "canonical_label": "Business AI Agents",
            "label_vi": "Business AI Agents",
            "normalized_key": ROOT_KEY,
            "description": "Canonical root for the Business AI Agents knowledge system.",
            "scope_note": None,
            "primary_parent_id": None,
            "lifecycle_status": "approved",
            "created_by_type": "migration",
            "created_by_ref": "graph-intelligence-v2",
            "metadata": {"seed_version": "business-ai-agents-v1"},
            "created_at": now,
            "updated_at": now,
        }
    ]
    rows.extend(
        {
            "id": ontology_id(key),
            "node_type": "SystemPillar",
            "canonical_label": label,
            "label_vi": label_vi,
            "normalized_key": key,
            "description": f"Canonical Business AI Agents pillar: {label}.",
            "scope_note": None,
            "primary_parent_id": root_id,
            "lifecycle_status": "approved",
            "created_by_type": "migration",
            "created_by_ref": "graph-intelligence-v2",
            "metadata": {"seed_version": "business-ai-agents-v1"},
            "created_at": now,
            "updated_at": now,
        }
        for key, label, label_vi in PILLARS
    )
    op.bulk_insert(nodes, rows)


def downgrade() -> None:
    op.drop_table("graph_mutations")
    op.drop_table("graph_change_sets")
    op.drop_table("node_evidence")
    op.drop_table("concept_aliases")
    op.drop_table("knowledge_edges")
    op.drop_table("knowledge_nodes")
