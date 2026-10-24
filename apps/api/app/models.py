import uuid
from datetime import UTC, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.core.identity import current_actor_id
from app.db import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


research_tags = Table(
    "research_tags",
    Base.metadata,
    Column(
        "research_id",
        String(36),
        ForeignKey("research_items.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        String(36),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
        # The composite primary key only serves lookups starting at research_id. Finding
        # research by tag goes the other way and needs its own index.
        index=True,
    ),
)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class PortableVector(TypeDecorator[Any]):
    """Use pgvector in PostgreSQL while keeping SQLite contract tests portable."""

    impl = JSON
    cache_ok = True

    def __init__(self, dimensions: int) -> None:
        super().__init__()
        self.dimensions = dimensions

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Vector(self.dimensions))
        return dialect.type_descriptor(JSON())


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('owner', 'researcher', 'viewer')", name="ck_users_role"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(30), default="researcher")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    password_hash: Mapped[str | None] = mapped_column(Text)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ServiceAccount(TimestampMixin, Base):
    __tablename__ = "service_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200))
    source_namespace: Mapped[str] = mapped_column(String(120), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    token_prefix: Mapped[str] = mapped_column(String(20))
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(120))


class ResearchItem(TimestampMixin, Base):
    __tablename__ = "research_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    display_id: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500), index=True)
    type: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    collection_method: Mapped[str] = mapped_column(String(30), default="manual", index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str | None] = mapped_column(String(2000), index=True)
    external_id: Mapped[str | None] = mapped_column(String(500))
    authors: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tags: Mapped[list["Tag"]] = relationship(secondary=research_tags, lazy="selectin")
    versions: Mapped[list["ResearchVersion"]] = relationship(
        back_populates="research", cascade="all, delete-orphan"
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="research", cascade="all, delete-orphan"
    )


class ResearchVersion(Base):
    __tablename__ = "research_versions"
    __table_args__ = (UniqueConstraint("research_id", "version_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    research_id: Mapped[str] = mapped_column(
        ForeignKey("research_items.id", ondelete="CASCADE"), index=True
    )
    version_number: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    research: Mapped[ResearchItem] = relationship(back_populates="versions")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100))


class ResearchRelation(Base):
    __tablename__ = "research_relations"
    __table_args__ = (UniqueConstraint("source_id", "target_id", "relation_type"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("research_items.id", ondelete="CASCADE"), index=True
    )
    target_id: Mapped[str] = mapped_column(
        ForeignKey("research_items.id", ondelete="CASCADE"), index=True
    )
    relation_type: Mapped[str] = mapped_column(String(40))
    discovered_by: Mapped[str] = mapped_column(String(20), default="manual")
    confidence: Mapped[float | None] = mapped_column(Float)
    reasoning: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    research_id: Mapped[str] = mapped_column(
        ForeignKey("research_items.id", ondelete="CASCADE"), index=True
    )
    author: Mapped[str] = mapped_column(String(120), default="Nhà nghiên cứu cục bộ")
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    research: Mapped[ResearchItem] = relationship(back_populates="comments")


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    research_id: Mapped[str] = mapped_column(
        ForeignKey("research_items.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(500))
    object_key: Mapped[str] = mapped_column(String(1000), unique=True)
    mime_type: Mapped[str] = mapped_column(String(200))
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(80))
    actor: Mapped[str] = mapped_column(String(120), default=current_actor_id)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    aggregate_id: Mapped[str] = mapped_column(String(36), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AIOutput(Base):
    __tablename__ = "ai_outputs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    research_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_items.id", ondelete="CASCADE"), index=True
    )
    task: Mapped[str] = mapped_column(String(50))
    model_name: Mapped[str] = mapped_column(String(120))
    model_version: Mapped[str] = mapped_column(String(120))
    prompt_version: Mapped[str] = mapped_column(String(50))
    input_hash: Mapped[str] = mapped_column(String(64), index=True)
    output_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EmbeddingChunk(Base):
    __tablename__ = "embedding_chunks"
    __table_args__ = (UniqueConstraint("research_id", "chunk_index"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    research_id: Mapped[str] = mapped_column(
        ForeignKey("research_items.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SearchVectorProjection(TimestampMixin, Base):
    __tablename__ = "search_vector_projections"
    __table_args__ = (
        UniqueConstraint("research_id", "chunk_index"),
        Index(
            "ix_search_vector_projections_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    research_id: Mapped[str] = mapped_column(
        ForeignKey("research_items.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    embedding: Mapped[list[float]] = mapped_column(PortableVector(1024))
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(120))
    source_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sync_id: Mapped[str] = mapped_column(String(36), index=True)


class CollectorSource(Base):
    __tablename__ = "collector_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(30), default="rss")
    url: Mapped[str] = mapped_column(String(2000))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_approve_threshold: Mapped[float] = mapped_column(Float, default=80)
    auto_reject_threshold: Mapped[float] = mapped_column(Float, default=50)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CollectorRun(Base):
    __tablename__ = "collector_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("collector_sources.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="running")
    discovered_count: Mapped[int] = mapped_column(Integer, default=0)
    ingested_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DiscoveredItem(Base):
    __tablename__ = "discovered_items"
    __table_args__ = (UniqueConstraint("source_id", "external_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("collector_sources.id", ondelete="CASCADE"), index=True
    )
    run_id: Mapped[str] = mapped_column(
        ForeignKey("collector_runs.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[str] = mapped_column(String(2000))
    title: Mapped[str] = mapped_column(String(500))
    normalized_markdown: Mapped[str] = mapped_column(Text, default="")
    authors: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="discovered", index=True)
    score: Mapped[float | None] = mapped_column(Float)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    research_id: Mapped[str | None] = mapped_column(ForeignKey("research_items.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LinkSubmission(TimestampMixin, Base):
    __tablename__ = "link_submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    url: Mapped[str] = mapped_column(String(2000), unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(40), default="manual", index=True)
    source_ref: Mapped[str | None] = mapped_column(String(500), index=True)
    submitted_by: Mapped[str] = mapped_column(String(200), default="local-user")
    status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    stage: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    review_status: Mapped[str] = mapped_column(String(40), default="not_requested", index=True)
    title: Mapped[str | None] = mapped_column(String(500))
    extracted_markdown: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    classification: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_overrides: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    provider_name: Mapped[str | None] = mapped_column(String(80))
    model_name: Mapped[str | None] = mapped_column(String(200))
    auto_approve: Mapped[bool] = mapped_column(Boolean, default=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(80), index=True)
    error_details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    research_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_items.id", ondelete="SET NULL"), index=True
    )
    # Set when this submission repeats a source already in the queue. Kept as a link rather
    # than a status alone so a reviewer can open the original, and so the duplicate can
    # inherit the research record once that original is published.
    duplicate_of_id: Mapped[str | None] = mapped_column(
        ForeignKey("link_submissions.id", ondelete="SET NULL"), index=True
    )


class IntakeReceipt(Base):
    __tablename__ = "intake_receipts"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('manual', 'api', 'discord')", name="ck_intake_receipt_source_type"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_type: Mapped[str] = mapped_column(String(40), index=True)
    source_namespace: Mapped[str] = mapped_column(String(120), index=True)
    external_occurrence_ref: Mapped[str] = mapped_column(String(500))
    delivery_key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    container_ref: Mapped[str | None] = mapped_column(String(200))
    submitted_by: Mapped[str] = mapped_column(String(200), index=True)
    external_actor_ref_hash: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    delivery_count: Mapped[int] = mapped_column(Integer, default=1)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class IntakeReceiptItem(Base):
    __tablename__ = "intake_receipt_items"
    __table_args__ = (
        CheckConstraint("kind IN ('url', 'document')", name="ck_intake_receipt_item_kind"),
        CheckConstraint(
            "initial_disposition IN ('queued', 'linked_existing')",
            name="ck_intake_receipt_item_disposition",
        ),
        CheckConstraint(
            "((link_submission_id IS NOT NULL AND document_workspace_id IS NULL) OR "
            "(link_submission_id IS NULL AND document_workspace_id IS NOT NULL))",
            name="ck_intake_receipt_item_one_target",
        ),
        UniqueConstraint("receipt_id", "ordinal", name="uq_intake_receipt_item_ordinal"),
        UniqueConstraint("receipt_id", "item_key_hash", name="uq_intake_receipt_item_key"),
        UniqueConstraint(
            "receipt_id",
            "kind",
            "external_item_ref",
            name="uq_intake_receipt_document_ref",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    receipt_id: Mapped[str] = mapped_column(
        ForeignKey("intake_receipts.id", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(20), index=True)
    item_key_hash: Mapped[str] = mapped_column(String(64))
    normalized_url: Mapped[str | None] = mapped_column(String(2000))
    external_item_ref: Mapped[str | None] = mapped_column(String(500))
    content_sha256: Mapped[str | None] = mapped_column(String(64))
    link_submission_id: Mapped[str | None] = mapped_column(
        ForeignKey("link_submissions.id", ondelete="RESTRICT"), index=True
    )
    document_workspace_id: Mapped[str | None] = mapped_column(
        ForeignKey("document_graph_workspaces.id", ondelete="RESTRICT"), index=True
    )
    initial_disposition: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    discovered_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("discovered_items.id", ondelete="CASCADE"), index=True
    )
    research_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_items.id", ondelete="CASCADE"), index=True
    )
    overall_score: Mapped[float] = mapped_column(Float)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    decision: Mapped[str] = mapped_column(String(30), index=True)
    reasoning: Mapped[str | None] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(String(120), default="deterministic-v1")
    prompt_version: Mapped[str] = mapped_column(String(50), default="collector-score-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class KnowledgeGap(TimestampMixin, Base):
    __tablename__ = "knowledge_gaps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    key: Mapped[str] = mapped_column(String(240), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    concept_key: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(40), default="detected", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=50, index=True)
    coverage_count: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[str] = mapped_column(Text)
    assigned_to: Mapped[str | None] = mapped_column(String(200))
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deep_research_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_items.id", ondelete="SET NULL"), index=True
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class KnowledgeNode(TimestampMixin, Base):
    __tablename__ = "knowledge_nodes"
    __table_args__ = (
        UniqueConstraint("node_type", "normalized_key", name="uq_knowledge_node_type_key"),
        CheckConstraint(
            "primary_parent_id IS NULL OR primary_parent_id <> id", name="ck_node_parent"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    node_type: Mapped[str] = mapped_column(String(60), index=True)
    canonical_label: Mapped[str] = mapped_column(String(250))
    label_vi: Mapped[str | None] = mapped_column(String(250))
    normalized_key: Mapped[str] = mapped_column(String(250), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    scope_note: Mapped[str | None] = mapped_column(Text)
    primary_parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_nodes.id", ondelete="SET NULL"), index=True
    )
    lifecycle_status: Mapped[str] = mapped_column(String(30), default="approved", index=True)
    created_by_type: Mapped[str] = mapped_column(String(30), default="human")
    created_by_ref: Mapped[str | None] = mapped_column(String(100))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class KnowledgeEdge(TimestampMixin, Base):
    __tablename__ = "knowledge_edges"
    __table_args__ = (
        UniqueConstraint(
            "source_node_id",
            "target_node_id",
            "edge_type",
            "lifecycle_status",
            name="uq_active_knowledge_edge",
        ),
        CheckConstraint("source_node_id <> target_node_id", name="ck_knowledge_edge_self_loop"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_edge_confidence"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_node_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), index=True
    )
    target_node_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), index=True
    )
    edge_type: Mapped[str] = mapped_column(String(60), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1)
    lifecycle_status: Mapped[str] = mapped_column(String(30), default="approved", index=True)
    evidence_status: Mapped[str] = mapped_column(String(30), default="supported")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by_type: Mapped[str] = mapped_column(String(30), default="human")
    created_by_ref: Mapped[str | None] = mapped_column(String(100))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class ConceptAlias(TimestampMixin, Base):
    __tablename__ = "concept_aliases"
    __table_args__ = (
        UniqueConstraint("normalized_alias", "language", name="uq_concept_alias_language"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    knowledge_node_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), index=True
    )
    alias: Mapped[str] = mapped_column(String(250))
    normalized_alias: Mapped[str] = mapped_column(String(250), index=True)
    language: Mapped[str] = mapped_column(String(12), default="en")
    alias_type: Mapped[str] = mapped_column(String(30), default="synonym")
    lifecycle_status: Mapped[str] = mapped_column(String(30), default="approved", index=True)
    created_by_type: Mapped[str] = mapped_column(String(30), default="human")
    created_by_ref: Mapped[str | None] = mapped_column(String(100))


class NodeEvidence(Base):
    __tablename__ = "node_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_kind: Mapped[str] = mapped_column(String(30), index=True)
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    source_document_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_items.id", ondelete="SET NULL"), index=True
    )
    location: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    excerpt: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    extraction_method: Mapped[str | None] = mapped_column(String(60))
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GraphChangeSet(TimestampMixin, Base):
    __tablename__ = "graph_change_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    origin_type: Mapped[str] = mapped_column(String(30), index=True)
    origin_id: Mapped[str | None] = mapped_column(String(36), index=True)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text, default="")
    lifecycle_status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    validation_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(120), default="local-user")
    approved_by: Mapped[str | None] = mapped_column(String(120))
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GraphMutation(TimestampMixin, Base):
    __tablename__ = "graph_mutations"
    __table_args__ = (UniqueConstraint("change_set_id", "mutation_order"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    change_set_id: Mapped[str] = mapped_column(
        ForeignKey("graph_change_sets.id", ondelete="CASCADE"), index=True
    )
    mutation_order: Mapped[int] = mapped_column(Integer)
    operation: Mapped[str] = mapped_column(String(40), index=True)
    target_kind: Mapped[str] = mapped_column(String(20))
    target_id: Mapped[str | None] = mapped_column(String(36), index=True)
    before_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    proposed_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    validation_status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    validation_messages: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    review_decision: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(120))


class ChatSession(TimestampMixin, Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        CheckConstraint(
            "credential_source IN ('system', 'personal')", name="ck_chat_credential_source"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(300), default="Cuộc trao đổi mới")
    scope_type: Mapped[str] = mapped_column(String(30), default="graph", index=True)
    scope_id: Mapped[str | None] = mapped_column(String(36), index=True)
    provider_name: Mapped[str] = mapped_column(String(50), default="openai", index=True)
    credential_source: Mapped[str] = mapped_column(
        String(20), default="system", server_default="system"
    )
    model_name: Mapped[str] = mapped_column(String(200))
    conversation_summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    prompt_version: Mapped[str] = mapped_column(String(80), default="graph-chat-v1")
    source_type: Mapped[str] = mapped_column(String(30), default="local", server_default="local")
    source_url: Mapped[str | None] = mapped_column(String(2000))
    source_snapshot_hash: Mapped[str | None] = mapped_column(String(64))
    source_imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    imported_message_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20), index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    provider_response_id: Mapped[str | None] = mapped_column(String(200), index=True)
    provider_request_id: Mapped[str | None] = mapped_column(String(200))
    tool_calls_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    tool_results_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    linked_change_set_id: Mapped[str | None] = mapped_column(
        ForeignKey("graph_change_sets.id", ondelete="SET NULL"), index=True
    )
    usage_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(80), index=True)
    origin_type: Mapped[str] = mapped_column(String(30), default="local", server_default="local")
    media_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, server_default="[]"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DocumentGraphWorkspace(TimestampMixin, Base):
    __tablename__ = "document_graph_workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    research_id: Mapped[str] = mapped_column(
        ForeignKey("research_items.id", ondelete="CASCADE"), index=True
    )
    attachment_id: Mapped[str] = mapped_column(
        ForeignKey("attachments.id", ondelete="CASCADE"), unique=True, index=True
    )
    storage_object_key: Mapped[str] = mapped_column(String(1000), unique=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    processing_status: Mapped[str] = mapped_column(String(40), default="uploaded", index=True)
    review_status: Mapped[str] = mapped_column(String(40), default="not_requested", index=True)
    extraction_limitations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    error_code: Mapped[str | None] = mapped_column(String(80), index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    provider_name: Mapped[str | None] = mapped_column(String(80))
    model_name: Mapped[str | None] = mapped_column(String(200))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extracted_char_count: Mapped[int] = mapped_column(Integer, default=0)
    source_version: Mapped[int] = mapped_column(Integer, default=1)
    rag_status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    rag_chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    rag_indexed_version: Mapped[int | None] = mapped_column(Integer)
    rag_error_code: Mapped[str | None] = mapped_column(String(80), index=True)
    rag_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DocumentSourceVersion(Base):
    __tablename__ = "document_source_versions"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "version_number", name="uq_document_source_version_number"
        ),
        CheckConstraint("version_number >= 1", name="ck_document_source_version_positive"),
        CheckConstraint("size_bytes >= 0", name="ck_document_source_version_size"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("document_graph_workspaces.id", ondelete="CASCADE"), index=True
    )
    version_number: Mapped[int] = mapped_column(Integer)
    object_key: Mapped[str] = mapped_column(String(1000), unique=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    origin: Mapped[str] = mapped_column(String(30), index=True)
    change_summary: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[str] = mapped_column(String(120), default=current_actor_id)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DocumentAIEditProposal(TimestampMixin, Base):
    __tablename__ = "document_ai_edit_proposals"
    __table_args__ = (
        CheckConstraint("selection_start >= 0", name="ck_document_ai_edit_start"),
        CheckConstraint("selection_end > selection_start", name="ck_document_ai_edit_range"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("document_graph_workspaces.id", ondelete="CASCADE"), index=True
    )
    base_version_number: Mapped[int] = mapped_column(Integer)
    selection_start: Mapped[int] = mapped_column(Integer)
    selection_end: Mapped[int] = mapped_column(Integer)
    selected_text_hash: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(40))
    instruction: Mapped[str | None] = mapped_column(String(1000))
    replacement_text: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(String(1000), default="")
    provider_name: Mapped[str] = mapped_column(String(50))
    model_name: Mapped[str] = mapped_column(String(200))
    prompt_version: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    accepted_version_number: Mapped[int | None] = mapped_column(Integer)
    created_by: Mapped[str] = mapped_column(String(120), default=current_actor_id)
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DocumentGraphNode(TimestampMixin, Base):
    __tablename__ = "document_graph_nodes"
    __table_args__ = (
        UniqueConstraint("workspace_id", "local_key", name="uq_document_node_local_key"),
        CheckConstraint(
            "parent_node_id IS NULL OR parent_node_id <> id", name="ck_document_node_parent"
        ),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_document_node_confidence"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("document_graph_workspaces.id", ondelete="CASCADE"), index=True
    )
    local_key: Mapped[str] = mapped_column(String(80))
    node_type: Mapped[str] = mapped_column(String(40), index=True)
    label: Mapped[str] = mapped_column(String(250))
    summary: Mapped[str] = mapped_column(Text, default="")
    parent_node_id: Mapped[str | None] = mapped_column(
        ForeignKey("document_graph_nodes.id", ondelete="SET NULL"), index=True
    )
    confidence: Mapped[float] = mapped_column(Float, default=0)
    evidence_status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class DocumentGraphEdge(TimestampMixin, Base):
    __tablename__ = "document_graph_edges"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "source_node_id",
            "target_node_id",
            "edge_type",
            name="uq_document_graph_edge",
        ),
        CheckConstraint(
            "source_node_id <> target_node_id", name="ck_document_graph_edge_self_loop"
        ),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_document_edge_confidence"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("document_graph_workspaces.id", ondelete="CASCADE"), index=True
    )
    source_node_id: Mapped[str] = mapped_column(
        ForeignKey("document_graph_nodes.id", ondelete="CASCADE"), index=True
    )
    target_node_id: Mapped[str] = mapped_column(
        ForeignKey("document_graph_nodes.id", ondelete="CASCADE"), index=True
    )
    edge_type: Mapped[str] = mapped_column(String(60), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    evidence_status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class PaperEvaluation(Base):
    __tablename__ = "paper_evaluations"
    __table_args__ = (
        CheckConstraint(
            "fit_score IS NULL OR (fit_score >= 0 AND fit_score <= 100)", name="ck_paper_fit_score"
        ),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_paper_confidence"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("document_graph_workspaces.id", ondelete="CASCADE"), unique=True, index=True
    )
    rubric_version: Mapped[str] = mapped_column(String(100), index=True)
    dimension_scores: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    fit_score: Mapped[float | None] = mapped_column(Float)
    decision: Mapped[str] = mapped_column(String(40), index=True)
    failed_gates: Mapped[list[str]] = mapped_column(JSON, default=list)
    matched_pillars: Mapped[list[str]] = mapped_column(JSON, default=list)
    candidate_parents: Mapped[list[str]] = mapped_column(JSON, default=list)
    contribution_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    overlaps_with: Mapped[list[str]] = mapped_column(JSON, default=list)
    fills_gaps: Mapped[list[str]] = mapped_column(JSON, default=list)
    limitations: Mapped[list[str]] = mapped_column(JSON, default=list)
    reasoning_summary: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0)
    provider_name: Mapped[str | None] = mapped_column(String(80))
    model_name: Mapped[str | None] = mapped_column(String(200))
    prompt_version: Mapped[str | None] = mapped_column(String(100))
    input_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
