"""Initial migration: core tables

Revision ID: 097c8293450b
Revises:
Create Date: 2025-11-03 16:27:33.620419

Creates core tables for S1-04:
- user: User accounts with authentication and authorization
- participant: Participants in proficiency assessment
- file_ref: File storage references (LOCAL/MINIO abstraction)
- report: Reports uploaded for participants
- prof_activity: Professional activity domains

All tables include proper indexes, constraints, and foreign keys.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "097c8293450b"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Create core tables with indexes and constraints.
    """

    # ===== user table =====
    op.create_table(
        "user",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="USER"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("approved_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="user_pkey"),
        sa.UniqueConstraint("email", name="user_email_unique"),
        sa.CheckConstraint("role IN ('ADMIN', 'USER')", name="user_role_check"),
        sa.CheckConstraint("status IN ('PENDING', 'ACTIVE', 'DISABLED')", name="user_status_check"),
    )
    op.create_index("ix_user_email", "user", ["email"], unique=True)

    # ===== participant table =====
    op.create_table(
        "participant",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("external_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="participant_pkey"),
    )
    op.create_index("ix_participant_full_name", "participant", ["full_name"], unique=False)
    op.create_index("ix_participant_external_id", "participant", ["external_id"], unique=False)

    # ===== file_ref table =====
    op.create_table(
        "file_ref",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("storage", sa.String(length=20), nullable=False, server_default="LOCAL"),
        sa.Column("bucket", sa.String(length=100), nullable=False),
        sa.Column("key", sa.String(length=500), nullable=False),
        sa.Column("mime", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="file_ref_pkey"),
        sa.UniqueConstraint("storage", "bucket", "key", name="file_ref_location_unique"),
        sa.CheckConstraint("storage IN ('LOCAL', 'MINIO')", name="file_ref_storage_check"),
        sa.CheckConstraint("size_bytes >= 0", name="file_ref_size_check"),
    )
    op.create_index("idx_file_ref_storage", "file_ref", ["storage"], unique=False)

    # ===== prof_activity table =====
    op.create_table(
        "prof_activity",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="prof_activity_pkey"),
        sa.UniqueConstraint("code", name="prof_activity_code_unique"),
    )
    op.create_index("ix_prof_activity_code", "prof_activity", ["code"], unique=True)

    # ===== report table =====
    op.create_table(
        "report",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="UPLOADED"),
        sa.Column("file_ref_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "uploaded_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("extracted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("extract_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="report_pkey"),
        sa.ForeignKeyConstraint(
            ["participant_id"],
            ["participant.id"],
            name="report_participant_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["file_ref_id"],
            ["file_ref.id"],
            name="report_file_ref_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("participant_id", "type", name="report_participant_type_unique"),
        sa.CheckConstraint(
            "type IN ('REPORT_1', 'REPORT_2', 'REPORT_3')", name="report_type_check"
        ),
        sa.CheckConstraint(
            "status IN ('UPLOADED', 'EXTRACTED', 'FAILED')", name="report_status_check"
        ),
    )
    op.create_index("idx_report_status", "report", ["status"], unique=False)
    op.create_index("idx_report_participant", "report", ["participant_id"], unique=False)


def downgrade() -> None:
    """
    Drop all core tables in reverse order (respecting foreign keys).
    """
    op.drop_table("report")
    op.drop_table("prof_activity")
    op.drop_table("file_ref")
    op.drop_table("participant")
    op.drop_table("user")
