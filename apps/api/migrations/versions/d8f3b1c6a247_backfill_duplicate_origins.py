"""Point existing duplicates at the submission they repeat.

``b6d9f1a3c527`` added ``duplicate_of_id`` but left every row already marked ``duplicate``
with a null value, so those rows still had no route back: nothing said what they
duplicated, and they could never inherit a research record when the original was published.
The live database had four of them.

The original is the earliest earlier submission sharing this row's content hash. Its
*current* review status is deliberately not consulted: the question a backfill answers is
"what did this row duplicate when it was recorded", and every one of the four rows in the
live database duplicated something that was rejected afterwards. Excluding those would
leave exactly the rows this migration exists to explain still unexplained.

Revision ID: d8f3b1c6a247
Revises: c7e2a5b8d431
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d8f3b1c6a247"
down_revision: str | None = "c7e2a5b8d431"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    stranded = connection.execute(
        sa.text(
            """
            SELECT id, content_hash, created_at
            FROM link_submissions
            WHERE review_status = 'duplicate' AND duplicate_of_id IS NULL
              AND content_hash IS NOT NULL
            """
        )
    ).fetchall()

    for row in stranded:
        original = connection.execute(
            sa.text(
                """
                SELECT id FROM link_submissions
                WHERE id <> :id
                  AND content_hash = :content_hash
                  AND created_at <= :created_at
                ORDER BY created_at
                LIMIT 1
                """
            ),
            {"id": row.id, "content_hash": row.content_hash, "created_at": row.created_at},
        ).scalar()
        if original is None:
            continue
        connection.execute(
            sa.text("UPDATE link_submissions SET duplicate_of_id = :origin WHERE id = :id"),
            {"origin": original, "id": row.id},
        )


def downgrade() -> None:
    # The column itself is removed by b6d9f1a3c527; clearing the backfilled values here
    # keeps a partial downgrade from leaving inferred data behind as though it were
    # recorded at the time.
    op.execute(
        sa.text(
            "UPDATE link_submissions SET duplicate_of_id = NULL WHERE review_status = 'duplicate'"
        )
    )
