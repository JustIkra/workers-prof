"""
Repository layer for ParticipantMetric data access (S2-08).

Handles all database operations for participant's actual metrics with upsert logic.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ParticipantMetric, Report


class ParticipantMetricRepository:
    """Repository for participant metric database operations with upsert logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert(
        self,
        participant_id: UUID,
        metric_code: str,
        value: Decimal,
        confidence: Decimal | None,
        source_report_id: UUID,
    ) -> ParticipantMetric:
        """
        Upsert a participant metric with priority rules.

        Priority rules:
        1. More recent report.uploaded_at takes precedence
        2. On tie, higher confidence value is preferred

        Args:
            participant_id: UUID of the participant
            metric_code: Metric code (e.g., "competency_1")
            value: Metric value (range 1-10)
            confidence: Confidence score (0-1)
            source_report_id: UUID of the source report

        Returns:
            Created or updated ParticipantMetric instance
        """
        # Get the report timestamp for priority comparison
        report_result = await self.db.execute(
            select(Report.uploaded_at).where(Report.id == source_report_id)
        )
        report_uploaded_at = report_result.scalar_one()

        # Check if metric already exists
        existing = await self.get_by_participant_and_code(participant_id, metric_code)

        if existing:
            # Get the existing report timestamp
            existing_report_result = await self.db.execute(
                select(Report.uploaded_at).where(Report.id == existing.last_source_report_id)
            )
            existing_uploaded_at = existing_report_result.scalar_one_or_none()

            # Determine if we should update based on priority rules
            should_update = False

            if existing_uploaded_at is None:
                # No existing report timestamp, always update
                should_update = True
            elif report_uploaded_at > existing_uploaded_at:
                # New report is more recent
                should_update = True
            elif report_uploaded_at == existing_uploaded_at:
                # Same timestamp, check confidence
                existing_confidence = existing.confidence or Decimal("0")
                new_confidence = confidence or Decimal("0")
                if new_confidence >= existing_confidence:
                    should_update = True

            if should_update:
                # Update existing record
                existing.value = value
                existing.confidence = confidence
                existing.last_source_report_id = source_report_id
                existing.updated_at = datetime.utcnow()
                await self.db.commit()
                await self.db.refresh(existing)
                return existing
            else:
                # Keep existing record, don't update
                return existing
        else:
            # Insert new record
            new_metric = ParticipantMetric(
                participant_id=participant_id,
                metric_code=metric_code,
                value=value,
                confidence=confidence,
                last_source_report_id=source_report_id,
            )
            self.db.add(new_metric)
            await self.db.commit()
            await self.db.refresh(new_metric)
            return new_metric

    async def get_by_participant_and_code(
        self, participant_id: UUID, metric_code: str
    ) -> ParticipantMetric | None:
        """
        Get a participant metric by participant ID and metric code.

        Args:
            participant_id: UUID of the participant
            metric_code: Metric code

        Returns:
            ParticipantMetric if found, None otherwise
        """
        result = await self.db.execute(
            select(ParticipantMetric).where(
                and_(
                    ParticipantMetric.participant_id == participant_id,
                    ParticipantMetric.metric_code == metric_code,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_by_participant(self, participant_id: UUID) -> list[ParticipantMetric]:
        """
        List all metrics for a participant.

        Args:
            participant_id: UUID of the participant

        Returns:
            List of ParticipantMetric instances
        """
        result = await self.db.execute(
            select(ParticipantMetric)
            .where(ParticipantMetric.participant_id == participant_id)
            .order_by(ParticipantMetric.metric_code)
        )
        return list(result.scalars().all())

    async def get_metrics_dict(self, participant_id: UUID) -> dict[str, Decimal]:
        """
        Get participant metrics as a dictionary for scoring calculations.

        Args:
            participant_id: UUID of the participant

        Returns:
            Dictionary mapping metric_code to value
        """
        metrics = await self.list_by_participant(participant_id)
        return {metric.metric_code: metric.value for metric in metrics}

    async def delete_by_participant_and_code(
        self, participant_id: UUID, metric_code: str
    ) -> bool:
        """
        Delete a participant metric.

        Args:
            participant_id: UUID of the participant
            metric_code: Metric code

        Returns:
            True if deleted, False if not found
        """
        metric = await self.get_by_participant_and_code(participant_id, metric_code)
        if metric:
            await self.db.delete(metric)
            await self.db.commit()
            return True
        return False

    async def update_value(
        self,
        participant_id: UUID,
        metric_code: str,
        value: Decimal,
        confidence: Decimal | None = None,
    ) -> ParticipantMetric | None:
        """
        Manually update a metric value (e.g., by admin).

        Args:
            participant_id: UUID of the participant
            metric_code: Metric code
            value: New metric value
            confidence: Optional new confidence score

        Returns:
            Updated ParticipantMetric if found, None otherwise
        """
        metric = await self.get_by_participant_and_code(participant_id, metric_code)
        if metric:
            metric.value = value
            if confidence is not None:
                metric.confidence = confidence
            metric.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(metric)
            return metric
        return None
