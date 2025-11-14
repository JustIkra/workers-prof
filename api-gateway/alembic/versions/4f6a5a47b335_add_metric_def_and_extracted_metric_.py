"""add_metric_def_and_extracted_metric_tables

Revision ID: 4f6a5a47b335
Revises: 8d1f97e2cf8d
Create Date: 2025-11-06 21:17:54.319189

Creates tables for S2-01:
- metric_def: Dictionary of metrics with validation ranges
- extracted_metric: Extracted metric values from reports with uniqueness constraint
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4f6a5a47b335"
down_revision: str | None = "8d1f97e2cf8d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Create metric_def and extracted_metric tables with proper indexes and constraints.
    """

    # ===== metric_def table =====
    op.create_table(
        "metric_def",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("min_value", sa.Numeric(10, 2), nullable=True),
        sa.Column("max_value", sa.Numeric(10, 2), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id", name="metric_def_pkey"),
        sa.UniqueConstraint("code", name="metric_def_code_unique"),
        sa.CheckConstraint(
            "min_value IS NULL OR max_value IS NULL OR min_value <= max_value",
            name="metric_def_range_check",
        ),
    )
    op.create_index("ix_metric_def_code", "metric_def", ["code"], unique=True)
    op.create_index("ix_metric_def_active", "metric_def", ["active"], unique=False)

    # ===== extracted_metric table =====
    op.create_table(
        "extracted_metric",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric_def_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("value", sa.Numeric(10, 2), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="OCR"),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="extracted_metric_pkey"),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["report.id"],
            name="extracted_metric_report_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["metric_def_id"],
            ["metric_def.id"],
            name="extracted_metric_metric_def_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "report_id", "metric_def_id", name="extracted_metric_report_metric_unique"
        ),
        sa.CheckConstraint(
            "source IN ('OCR', 'LLM', 'MANUAL')", name="extracted_metric_source_check"
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="extracted_metric_confidence_check",
        ),
    )
    op.create_index(
        "ix_extracted_metric_report_id", "extracted_metric", ["report_id"], unique=False
    )
    op.create_index(
        "ix_extracted_metric_metric_def_id", "extracted_metric", ["metric_def_id"], unique=False
    )


def downgrade() -> None:
    """
    Drop metric tables in reverse order (respecting foreign keys).
    """
    op.drop_table("extracted_metric")
    op.drop_table("metric_def")
