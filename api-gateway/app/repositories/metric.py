"""
Repository layer for Metric data access (S2-01).

Handles all database operations for metric definitions and extracted metrics.
"""

from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ExtractedMetric, MetricDef


class MetricDefRepository:
    """Repository for metric definition database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        code: str,
        name: str,
        description: Optional[str] = None,
        unit: Optional[str] = None,
        min_value: Optional[Decimal] = None,
        max_value: Optional[Decimal] = None,
        active: bool = True,
    ) -> MetricDef:
        """
        Create a new metric definition.

        Args:
            code: Unique metric code
            name: Metric name
            description: Optional description
            unit: Optional measurement unit
            min_value: Optional minimum value
            max_value: Optional maximum value
            active: Whether metric is active (default: True)

        Returns:
            Created MetricDef instance
        """
        metric_def = MetricDef(
            code=code,
            name=name,
            description=description,
            unit=unit,
            min_value=min_value,
            max_value=max_value,
            active=active,
        )
        self.db.add(metric_def)
        await self.db.commit()
        await self.db.refresh(metric_def)
        return metric_def

    async def get_by_id(self, metric_def_id: UUID) -> Optional[MetricDef]:
        """
        Get a metric definition by ID.

        Args:
            metric_def_id: UUID of the metric definition

        Returns:
            MetricDef if found, None otherwise
        """
        result = await self.db.execute(select(MetricDef).where(MetricDef.id == metric_def_id))
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[MetricDef]:
        """
        Get a metric definition by code.

        Args:
            code: Unique metric code

        Returns:
            MetricDef if found, None otherwise
        """
        result = await self.db.execute(select(MetricDef).where(MetricDef.code == code))
        return result.scalar_one_or_none()

    async def list_all(self, active_only: bool = False) -> list[MetricDef]:
        """
        List all metric definitions.

        Args:
            active_only: If True, return only active metrics

        Returns:
            List of MetricDef instances
        """
        stmt = select(MetricDef).order_by(MetricDef.code)
        if active_only:
            stmt = stmt.where(MetricDef.active == True)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        metric_def_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        unit: Optional[str] = None,
        min_value: Optional[Decimal] = None,
        max_value: Optional[Decimal] = None,
        active: Optional[bool] = None,
    ) -> Optional[MetricDef]:
        """
        Update a metric definition.

        Args:
            metric_def_id: UUID of the metric definition
            name: New name (if provided)
            description: New description (if provided)
            unit: New unit (if provided)
            min_value: New min_value (if provided)
            max_value: New max_value (if provided)
            active: New active status (if provided)

        Returns:
            Updated MetricDef if found, None otherwise
        """
        metric_def = await self.get_by_id(metric_def_id)
        if not metric_def:
            return None

        if name is not None:
            metric_def.name = name
        if description is not None:
            metric_def.description = description
        if unit is not None:
            metric_def.unit = unit
        if min_value is not None:
            metric_def.min_value = min_value
        if max_value is not None:
            metric_def.max_value = max_value
        if active is not None:
            metric_def.active = active

        await self.db.commit()
        await self.db.refresh(metric_def)
        return metric_def

    async def delete(self, metric_def_id: UUID) -> bool:
        """
        Delete a metric definition.

        Args:
            metric_def_id: UUID of the metric definition

        Returns:
            True if deleted, False if not found
        """
        metric_def = await self.get_by_id(metric_def_id)
        if not metric_def:
            return False

        await self.db.delete(metric_def)
        await self.db.commit()
        return True


class ExtractedMetricRepository:
    """Repository for extracted metric database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_or_update(
        self,
        report_id: UUID,
        metric_def_id: UUID,
        value: Decimal,
        source: str = "MANUAL",
        confidence: Optional[Decimal] = None,
        notes: Optional[str] = None,
    ) -> ExtractedMetric:
        """
        Create or update an extracted metric.
        If (report_id, metric_def_id) already exists, update it; otherwise create new.

        Args:
            report_id: UUID of the report
            metric_def_id: UUID of the metric definition
            value: Extracted value
            source: Source of extraction (OCR, LLM, MANUAL)
            confidence: Confidence score (0-1)
            notes: Additional notes

        Returns:
            Created or updated ExtractedMetric instance
        """
        # Check if exists
        existing = await self.get_by_report_and_metric(report_id, metric_def_id)

        if existing:
            # Update existing
            existing.value = value
            existing.source = source
            existing.confidence = confidence
            existing.notes = notes
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        else:
            # Create new
            extracted_metric = ExtractedMetric(
                report_id=report_id,
                metric_def_id=metric_def_id,
                value=value,
                source=source,
                confidence=confidence,
                notes=notes,
            )
            self.db.add(extracted_metric)
            await self.db.commit()
            await self.db.refresh(extracted_metric)
            return extracted_metric

    async def get_by_id(self, extracted_metric_id: UUID) -> Optional[ExtractedMetric]:
        """
        Get an extracted metric by ID.

        Args:
            extracted_metric_id: UUID of the extracted metric

        Returns:
            ExtractedMetric if found, None otherwise
        """
        result = await self.db.execute(
            select(ExtractedMetric)
            .options(selectinload(ExtractedMetric.metric_def))
            .where(ExtractedMetric.id == extracted_metric_id)
        )
        return result.scalar_one_or_none()

    async def get_by_report_and_metric(
        self, report_id: UUID, metric_def_id: UUID
    ) -> Optional[ExtractedMetric]:
        """
        Get an extracted metric by report and metric definition.

        Args:
            report_id: UUID of the report
            metric_def_id: UUID of the metric definition

        Returns:
            ExtractedMetric if found, None otherwise
        """
        result = await self.db.execute(
            select(ExtractedMetric)
            .options(selectinload(ExtractedMetric.metric_def))
            .where(
                ExtractedMetric.report_id == report_id,
                ExtractedMetric.metric_def_id == metric_def_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_report(self, report_id: UUID) -> list[ExtractedMetric]:
        """
        List all extracted metrics for a report.

        Args:
            report_id: UUID of the report

        Returns:
            List of ExtractedMetric instances with metric_def loaded
        """
        result = await self.db.execute(
            select(ExtractedMetric)
            .options(selectinload(ExtractedMetric.metric_def))
            .where(ExtractedMetric.report_id == report_id)
            .order_by(ExtractedMetric.metric_def_id)
        )
        return list(result.scalars().all())

    async def get_by_participant(self, participant_id: UUID) -> list[ExtractedMetric]:
        """
        Get all extracted metrics for a participant across all their reports.

        Args:
            participant_id: UUID of the participant

        Returns:
            List of ExtractedMetric instances with metric_def loaded
        """
        # Import here to avoid circular dependency
        from app.db.models import Report

        result = await self.db.execute(
            select(ExtractedMetric)
            .join(Report, ExtractedMetric.report_id == Report.id)
            .options(selectinload(ExtractedMetric.metric_def))
            .where(Report.participant_id == participant_id)
            .order_by(ExtractedMetric.metric_def_id)
        )
        return list(result.scalars().all())

    async def delete(self, extracted_metric_id: UUID) -> bool:
        """
        Delete an extracted metric.

        Args:
            extracted_metric_id: UUID of the extracted metric

        Returns:
            True if deleted, False if not found
        """
        extracted_metric = await self.get_by_id(extracted_metric_id)
        if not extracted_metric:
            return False

        await self.db.delete(extracted_metric)
        await self.db.commit()
        return True

    async def delete_by_report(self, report_id: UUID) -> int:
        """
        Delete all extracted metrics for a report.

        Args:
            report_id: UUID of the report

        Returns:
            Number of metrics deleted
        """
        metrics = await self.list_by_report(report_id)
        count = len(metrics)
        for metric in metrics:
            await self.db.delete(metric)
        await self.db.commit()
        return count
