"""The migration chain itself, exercised rather than assumed.

Two defects lived here. A constraint was added with `op.create_foreign_key`, which SQLite
cannot do, so `alembic upgrade head` failed outright on the dialect this repository also
supports. And a column was added without backfilling the rows that needed it, leaving the
records it existed to explain still unexplained.
"""

import subprocess
import sys
from pathlib import Path

import pytest
import sqlalchemy as sa

API_ROOT = Path(__file__).resolve().parents[1]


def _alembic(database_url: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=API_ROOT,
        env={"PATH": "/usr/bin:/bin", "DATABASE_URL": database_url, "HOME": "/tmp"},
        capture_output=True,
        text=True,
        timeout=300,
    )


@pytest.fixture
def migrated_url(tmp_path) -> str:
    url = f"sqlite:///{tmp_path / 'chain.db'}"
    result = _alembic(url, "upgrade", "head")
    assert result.returncode == 0, result.stderr
    return url


def test_the_chain_applies_cleanly_on_sqlite(migrated_url):
    """SQLite cannot ALTER a constraint, so every such change must use batch mode."""

    result = _alembic(migrated_url, "current")

    assert result.returncode == 0, result.stderr
    assert "(head)" in result.stdout


def test_the_schema_the_chain_builds_matches_the_models(migrated_url):
    result = _alembic(migrated_url, "check")

    assert result.returncode == 0, result.stderr
    assert "No new upgrade operations detected" in result.stdout


def test_the_newest_migration_can_be_reversed_and_reapplied(migrated_url):
    down = _alembic(migrated_url, "downgrade", "-1")
    assert down.returncode == 0, down.stderr

    up = _alembic(migrated_url, "upgrade", "head")
    assert up.returncode == 0, up.stderr


def test_a_duplicate_recorded_before_the_column_existed_is_given_its_origin(tmp_path):
    """The rows this backfill exists for duplicated sources that were rejected later.

    Consulting the original's current review status would skip exactly those, which is how
    the first attempt at this backfill left all four live rows untouched.
    """

    url = f"sqlite:///{tmp_path / 'backfill.db'}"
    assert _alembic(url, "upgrade", "c7e2a5b8d431").returncode == 0

    engine = sa.create_engine(url)
    with engine.begin() as connection:
        for row_id, created, review_status in (
            ("original", "2026-01-01 00:00:00", "rejected"),
            ("copy", "2026-01-02 00:00:00", "duplicate"),
            ("unrelated", "2026-01-03 00:00:00", "duplicate"),
        ):
            connection.execute(
                sa.text(
                    """
                    INSERT INTO link_submissions
                        (id, url, source_type, submitted_by, status, stage, review_status,
                         extracted_markdown, content_hash, classification, source_overrides,
                         auto_approve, attempt_count, created_at, updated_at)
                    VALUES (:id, :url, 'manual', 'test', 'completed', 'completed', :review,
                            '', :hash, '{}', '{}', 0, 1, :created, :created)
                    """
                ),
                {
                    "id": row_id,
                    "url": f"https://example.com/{row_id}",
                    "review": review_status,
                    "hash": "shared-hash" if row_id != "unrelated" else "lonely-hash",
                    "created": created,
                },
            )

    assert _alembic(url, "upgrade", "head").returncode == 0

    with engine.connect() as connection:
        origins = dict(
            connection.execute(
                sa.text("SELECT id, duplicate_of_id FROM link_submissions")
            ).all()
        )

    assert origins["copy"] == "original"
    # A duplicate with nothing to point at is left null rather than guessed at.
    assert origins["unrelated"] is None
    assert origins["original"] is None
    engine.dispose()
