"""Seed professional activities

Revision ID: 3a015d9b6e41
Revises: 097c8293450b
Create Date: 2025-11-05 12:00:00.000000

Adds initial professional activities for S1-08 with idempotent upsert.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.db.seeds.prof_activity import PROF_ACTIVITY_SEED_DATA

# revision identifiers, used by Alembic.
revision: str = "3a015d9b6e41"
down_revision: str | None = "097c8293450b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Insert default prof_activity rows (idempotent)."""
    connection = op.get_bind()

    stmt = sa.text(
        """
        INSERT INTO prof_activity (id, code, name, description)
        VALUES (:id, :code, :name, :description)
        ON CONFLICT (code) DO UPDATE
        SET name = EXCLUDED.name,
            description = EXCLUDED.description
        """
    )

    for seed in PROF_ACTIVITY_SEED_DATA:
        connection.execute(
            stmt,
            {
                "id": str(seed.id),
                "code": seed.code,
                "name": seed.name,
                "description": seed.description,
            },
        )


def downgrade() -> None:
    """Remove default prof_activity rows."""
    connection = op.get_bind()
    delete_stmt = sa.text("DELETE FROM prof_activity WHERE code = :code")

    for seed in PROF_ACTIVITY_SEED_DATA:
        connection.execute(delete_stmt, {"code": seed.code})
