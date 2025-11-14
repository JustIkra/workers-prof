"""
Service layer for weight table operations.

Provides upload, listing, and activation workflows with validation rules.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProfActivity, WeightTable
from app.repositories.prof_activity import ProfActivityRepository
from app.repositories.weight_table import WeightTableRepository
from app.schemas.weight_table import (
    WeightItemResponse,
    WeightTableResponse,
    WeightTableUploadRequest,
)


class WeightTableService:
    """Business logic for managing weight tables."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.weight_repo = WeightTableRepository(db)
        self.prof_repo = ProfActivityRepository(db)

    async def upload_weight_table(self, payload: WeightTableUploadRequest) -> WeightTableResponse:
        """
        Create or update weight table for a professional activity.

        If a table already exists for the activity, it will be updated.
        Otherwise, a new table will be created.

        Raises:
            ValueError: If professional activity not found.
        """
        prof_activity = await self.prof_repo.get_by_code(payload.prof_activity_code)
        if not prof_activity:
            raise ValueError(f"Professional activity '{payload.prof_activity_code}' not found")

        weights_payload = [
            {"metric_code": item.metric_code, "weight": str(item.weight)}
            for item in payload.weights
        ]

        # Check if weight table already exists for this activity
        existing_table = await self.weight_repo.get_by_activity(prof_activity.id)

        if existing_table:
            # Update existing table
            weight_table = await self.weight_repo.update(
                weight_table=existing_table,
                weights=weights_payload,
                metadata=payload.metadata,
            )
        else:
            # Create new table
            weight_table = await self.weight_repo.create(
                prof_activity_id=prof_activity.id,
                weights=weights_payload,
                metadata=payload.metadata,
            )

        return self._serialize(weight_table, prof_activity=prof_activity)

    async def list_weight_tables(
        self,
        prof_activity_code: str | None = None,
    ) -> list[WeightTableResponse]:
        """List weight tables optionally filtered by professional activity code."""
        prof_activity: ProfActivity | None = None
        prof_activity_id: uuid.UUID | None = None

        if prof_activity_code:
            prof_activity = await self.prof_repo.get_by_code(prof_activity_code)
            if not prof_activity:
                raise ValueError(f"Professional activity '{prof_activity_code}' not found")
            prof_activity_id = prof_activity.id

        tables = await self.weight_repo.list_all(prof_activity_id=prof_activity_id)
        return [self._serialize(table) for table in tables]

    async def update_weight_table(
        self,
        weight_table_id: uuid.UUID,
        payload: WeightTableUploadRequest,
    ) -> WeightTableResponse:
        """
        Update an existing weight table.

        Raises:
            ValueError: If weight table not found or professional activity doesn't match.
        """
        weight_table = await self.weight_repo.get_by_id(weight_table_id)
        if not weight_table:
            raise ValueError("Weight table not found")

        prof_activity = await self.prof_repo.get_by_code(payload.prof_activity_code)
        if not prof_activity:
            raise ValueError(f"Professional activity '{payload.prof_activity_code}' not found")

        if weight_table.prof_activity_id != prof_activity.id:
            raise ValueError("Cannot change professional activity of existing weight table")

        weights_payload = [
            {"metric_code": item.metric_code, "weight": str(item.weight)}
            for item in payload.weights
        ]

        updated_table = await self.weight_repo.update(
            weight_table=weight_table,
            weights=weights_payload,
            metadata=payload.metadata,
        )

        return self._serialize(updated_table, prof_activity=prof_activity)

    def _serialize(
        self,
        weight_table: WeightTable,
        *,
        prof_activity: ProfActivity | None = None,
    ) -> WeightTableResponse:
        """Convert ORM entity to API schema."""
        activity = prof_activity or weight_table.prof_activity
        if not activity:
            raise ValueError("Weight table missing related professional activity")

        weights = [
            WeightItemResponse(
                metric_code=entry["metric_code"],
                weight=Decimal(str(entry["weight"])),
            )
            for entry in weight_table.weights
        ]

        return WeightTableResponse(
            id=weight_table.id,
            prof_activity_id=weight_table.prof_activity_id,
            prof_activity_code=activity.code,
            prof_activity_name=activity.name,
            weights=weights,
            metadata=weight_table.metadata_json,
            created_at=weight_table.created_at,
        )
