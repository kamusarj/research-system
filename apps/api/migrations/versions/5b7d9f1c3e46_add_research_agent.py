"""Research agent: question runs, progress events, sources, verified claims and web cache."""

import sqlalchemy as sa
from alembic import op

revision = "5b7d9f1c3e46"
down_revision = "4a6c8e0b2d35"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("stage", sa.String(30), nullable=False),
        sa.Column("variant", sa.String(30), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("provider_name", sa.String(80), nullable=True),
        sa.Column("model_name", sa.String(200), nullable=True),
        sa.Column("checkpoint_json", sa.JSON(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("report_markdown", sa.Text(), nullable=True),
        sa.Column(
            "report_research_id",
            sa.String(36),
            sa.ForeignKey("research_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "knowledge_gap_id",
            sa.String(36),
            sa.ForeignKey("knowledge_gaps.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_research_run_status",
        ),
    )
    op.create_index("ix_research_runs_queue", "research_runs", ["status", "next_attempt_at"])
    op.create_index("ix_research_runs_creator_day", "research_runs", ["created_by", "created_at"])
    op.create_table(
        "research_run_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("research_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("stage", sa.String(30), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_research_run_events_run_id", "research_run_events", ["run_id"])
    op.create_table(
        "research_run_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("research_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("perspective", sa.String(30), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.String(2000), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=True),
        sa.Column("simhash", sa.String(16), nullable=True),
        sa.Column("research_item_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("duplicate_of_id", sa.String(36), nullable=True),
        sa.Column("suspicious", sa.Boolean(), nullable=False),
        sa.Column("citation_index", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("run_id", "canonical_url", name="uq_run_source_url"),
    )
    op.create_index("ix_research_run_sources_run_id", "research_run_sources", ["run_id"])
    op.create_table(
        "research_run_claims",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("research_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.String(36),
            sa.ForeignKey("research_run_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("perspective", sa.String(30), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("matched_quote", sa.Text(), nullable=True),
        sa.Column("start_offset", sa.Integer(), nullable=True),
        sa.Column("end_offset", sa.Integer(), nullable=True),
        sa.Column("match_method", sa.String(20), nullable=False),
        sa.Column("entailment", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(80), nullable=True),
        sa.Column("used_in_report", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_research_run_claims_run_id", "research_run_claims", ["run_id"])
    op.create_index("ix_research_run_claims_source_id", "research_run_claims", ["source_id"])
    op.create_table(
        "research_web_cache",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("cache_key", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("cache_key"),
    )
    op.create_index("ix_research_web_cache_expires_at", "research_web_cache", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_research_web_cache_expires_at", table_name="research_web_cache")
    op.drop_table("research_web_cache")
    op.drop_index("ix_research_run_claims_source_id", table_name="research_run_claims")
    op.drop_index("ix_research_run_claims_run_id", table_name="research_run_claims")
    op.drop_table("research_run_claims")
    op.drop_index("ix_research_run_sources_run_id", table_name="research_run_sources")
    op.drop_table("research_run_sources")
    op.drop_index("ix_research_run_events_run_id", table_name="research_run_events")
    op.drop_table("research_run_events")
    op.drop_index("ix_research_runs_creator_day", table_name="research_runs")
    op.drop_index("ix_research_runs_queue", table_name="research_runs")
    op.drop_table("research_runs")
