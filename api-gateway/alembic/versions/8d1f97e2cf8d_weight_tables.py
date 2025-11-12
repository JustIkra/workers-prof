"""Add weight_table for professional activity weights

Revision ID: 8d1f97e2cf8d
Revises: 3a015d9b6e41
Create Date: 2025-11-06 10:00:00.000000

Creates weight_table to store JSON metric weights with versioning and activation rules.
Ensures only one active version per professional activity (partial unique index).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8d1f97e2cf8d"
down_revision: str | None = "3a015d9b6e41"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create weight_table with activation constraints."""
    op.create_table(
        "weight_table",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prof_activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("weights", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="weight_table_pkey"),
        sa.ForeignKeyConstraint(
            ["prof_activity_id"],
            ["prof_activity.id"],
            name="weight_table_prof_activity_id_fkey",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "prof_activity_id",
            "version",
            name="weight_table_prof_activity_version_unique",
        ),
        sa.CheckConstraint("version > 0", name="weight_table_version_positive"),
    )
    op.create_index(
        "idx_weight_table_prof_activity",
        "weight_table",
        ["prof_activity_id"],
        unique=False,
    )
    op.create_index(
        "uq_weight_table_prof_activity_active",
        "weight_table",
        ["prof_activity_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    """Drop weight_table and related indexes."""
    op.drop_index(
        "uq_weight_table_prof_activity_active",
        table_name="weight_table",
    )
    op.drop_index("idx_weight_table_prof_activity", table_name="weight_table")
    op.drop_table("weight_table")
