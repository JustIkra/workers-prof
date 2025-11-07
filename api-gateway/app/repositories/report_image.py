"""
Repository for report_image table operations.
"""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ReportImage


class ReportImageRepository:
    """Repository for managing report image records."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        report_id: uuid.UUID,
        file_ref_id: uuid.UUID,
        kind: str,
        page: int,
        order_index: int,
    ) -> ReportImage:
        """
        Create a new report image record.

        Args:
            report_id: UUID of the report
            file_ref_id: UUID of the file reference
            kind: Kind of image (TABLE or OTHER)
            page: Page number (0 for DOCX)
            order_index: Order within the report

        Returns:
            Created ReportImage instance
        """
        report_image = ReportImage(
            id=uuid.uuid4(),
            report_id=report_id,
            file_ref_id=file_ref_id,
            kind=kind,
            page=page,
            order_index=order_index,
        )
        self.session.add(report_image)
        await self.session.flush()
        return report_image

    async def get_by_report_id(self, report_id: uuid.UUID) -> Sequence[ReportImage]:
        """
        Get all images for a report, ordered by order_index.

        Args:
            report_id: UUID of the report

        Returns:
            List of ReportImage instances
        """
        stmt = (
            select(ReportImage)
            .where(ReportImage.report_id == report_id)
            .order_by(ReportImage.order_index)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_by_report_id(self, report_id: uuid.UUID) -> int:
        """
        Delete all images for a report.

        Args:
            report_id: UUID of the report

        Returns:
            Number of deleted records
        """
        images = await self.get_by_report_id(report_id)
        count = len(images)
        for image in images:
            await self.session.delete(image)
        await self.session.flush()
        return count
