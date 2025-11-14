"""
Repository for report and file_ref operations.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import FileRef, Participant, Report


class ReportRepository:
    """Data access methods for reports and associated file references."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def participant_exists(self, participant_id: UUID) -> bool:
        """Check if participant exists."""
        stmt = select(Participant.id).where(Participant.id == participant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create(self, report: Report, file_ref: FileRef) -> Report:
        """Persist report with associated file reference."""
        self.db.add(file_ref)
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        await self.db.refresh(file_ref)
        await self.db.refresh(report, attribute_names=["file_ref"])
        return report

    async def get_with_file_ref(self, report_id: UUID) -> Report | None:
        """Get report by ID with joined file reference."""
        stmt = select(Report).options(selectinload(Report.file_ref)).where(Report.id == report_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_by_participant(self, participant_id: UUID) -> list[Report]:
        """Get all reports for a participant."""
        stmt = (
            select(Report)
            .options(selectinload(Report.file_ref))
            .where(Report.participant_id == participant_id)
            .order_by(Report.uploaded_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, report: Report) -> None:
        """Delete report and commit."""
        await self.db.delete(report)
        await self.db.commit()
