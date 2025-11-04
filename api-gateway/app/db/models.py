"""
SQLAlchemy ORM models for core tables.

Implements the database schema for users, participants, files, reports, and professional activities.
Based on data-model.md ER diagram.
"""

import uuid
from datetime import date, datetime
from typing import Any, Literal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# ===== User Table =====
class User(Base):
    """
    User account for authentication and authorization.

    Roles:
    - ADMIN: Can approve users, upload weight tables, manage system
    - USER: Can view/upload reports for participants

    Status:
    - PENDING: Awaiting admin approval
    - ACTIVE: Approved and can access system
    - DISABLED: Account disabled
    """

    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="USER")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    approved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('ADMIN', 'USER')", name="user_role_check"),
        CheckConstraint(
            "status IN ('PENDING', 'ACTIVE', 'DISABLED')", name="user_status_check"
        ),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role}, status={self.status})>"


# ===== Participant Table =====
class Participant(Base):
    """
    Participant in proficiency assessment.

    Represents an individual whose competencies are being assessed.
    """

    __tablename__ = "participant"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relationships
    reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="participant", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Participant(id={self.id}, full_name={self.full_name})>"


# ===== FileRef Table =====
class FileRef(Base):
    """
    Reference to a file in storage (LOCAL or MINIO).

    Provides abstraction over storage backend.
    For LOCAL: bucket="local", key="reports/{participant_id}/{report_id}/original.docx"
    For MINIO: bucket="reports", key="{participant_id}/{report_id}/original.docx"
    """

    __tablename__ = "file_ref"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    storage: Mapped[str] = mapped_column(String(20), nullable=False, default="LOCAL")
    bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    key: Mapped[str] = mapped_column(String(500), nullable=False)
    mime: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("storage IN ('LOCAL', 'MINIO')", name="file_ref_storage_check"),
        CheckConstraint("size_bytes >= 0", name="file_ref_size_check"),
        # Unique constraint on (storage, bucket, key) to prevent duplicates
        UniqueConstraint("storage", "bucket", "key", name="file_ref_location_unique"),
        # Index for faster lookups by storage type
        Index("idx_file_ref_storage", "storage"),
    )

    def __repr__(self) -> str:
        return f"<FileRef(id={self.id}, storage={self.storage}, bucket={self.bucket}, key={self.key})>"


# ===== Report Table =====
class Report(Base):
    """
    Report uploaded for a participant.

    Types:
    - REPORT_1, REPORT_2, REPORT_3: Different report formats

    Status:
    - UPLOADED: File uploaded, extraction not started
    - EXTRACTED: Metrics extracted successfully
    - FAILED: Extraction failed
    """

    __tablename__ = "report"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("participant.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="UPLOADED")
    file_ref_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("file_ref.id", ondelete="RESTRICT"), nullable=False
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    extracted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    extract_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    participant: Mapped["Participant"] = relationship("Participant", back_populates="reports")
    file_ref: Mapped["FileRef"] = relationship("FileRef")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "type IN ('REPORT_1', 'REPORT_2', 'REPORT_3')", name="report_type_check"
        ),
        CheckConstraint(
            "status IN ('UPLOADED', 'EXTRACTED', 'FAILED')", name="report_status_check"
        ),
        # Only one report of each type per participant
        UniqueConstraint("participant_id", "type", name="report_participant_type_unique"),
        # Index for filtering by status
        Index("idx_report_status", "status"),
        # Index for participant lookup
        Index("idx_report_participant", "participant_id"),
    )

    def __repr__(self) -> str:
        return f"<Report(id={self.id}, participant_id={self.participant_id}, type={self.type}, status={self.status})>"


# ===== ProfActivity Table =====
class ProfActivity(Base):
    """
    Professional activity (профессиональная область).

    Represents a professional domain for which competencies are assessed.
    Examples: "developer", "analyst", "manager"
    """

    __tablename__ = "prof_activity"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight_tables: Mapped[list["WeightTable"]] = relationship(
        "WeightTable",
        back_populates="prof_activity",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ProfActivity(id={self.id}, code={self.code}, name={self.name})>"


# ===== WeightTable Table =====
class WeightTable(Base):
    """
    Weight table version for a professional activity.

    Stores metric weights as JSON structure and tracks activation status.
    Exactly one active version per professional activity is allowed.
    """

    __tablename__ = "weight_table"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prof_activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prof_activity.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    weights: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    prof_activity: Mapped["ProfActivity"] = relationship("ProfActivity", back_populates="weight_tables")

    __table_args__ = (
        UniqueConstraint(
            "prof_activity_id",
            "version",
            name="weight_table_prof_activity_version_unique",
        ),
        CheckConstraint("version > 0", name="weight_table_version_positive"),
        Index(
            "uq_weight_table_prof_activity_active",
            "prof_activity_id",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<WeightTable(id={self.id}, prof_activity_id={self.prof_activity_id}, "
            f"version={self.version}, is_active={self.is_active})>"
        )
