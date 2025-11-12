"""
Repository layer for weight tables.

Handles CRUD-style interactions with the weight_table table.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import WeightTable


class WeightTableRepository:
    """Repository for weight_table interactions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self, prof_activity_id: uuid.UUID | None = None) -> list[WeightTable]:
        """
        List weight tables, optionally filtered by professional activity.
        """
        stmt = (
            select(WeightTable)
            .options(selectinload(WeightTable.prof_activity))
            .order_by(WeightTable.prof_activity_id, WeightTable.created_at.desc())
        )

        if prof_activity_id:
            stmt = stmt.where(WeightTable.prof_activity_id == prof_activity_id)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, weight_table_id: uuid.UUID) -> WeightTable | None:
        """Fetch a weight table by its identifier."""
        stmt = (
            select(WeightTable)
            .options(selectinload(WeightTable.prof_activity))
            .where(WeightTable.id == weight_table_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_activity(self, prof_activity_id: uuid.UUID) -> WeightTable | None:
        """
        Get weight table for given professional activity.
        """
        stmt = (
            select(WeightTable)
            .options(selectinload(WeightTable.prof_activity))
            .where(WeightTable.prof_activity_id == prof_activity_id)
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        prof_activity_id: uuid.UUID,
        weights: list[dict[str, Any]],
        metadata: dict[str, Any] | None,
    ) -> WeightTable:
        """Create and persist a new weight table."""
        weight_table = WeightTable(
            id=uuid.uuid4(),
            prof_activity_id=prof_activity_id,
            weights=weights,
            metadata_json=metadata,
        )

        self.db.add(weight_table)
        await self.db.commit()
        await self.db.refresh(weight_table)
        return weight_table

    async def update(
        self,
        weight_table: WeightTable,
        weights: list[dict[str, Any]],
        metadata: dict[str, Any] | None,
    ) -> WeightTable:
        """Update existing weight table."""
        weight_table.weights = weights
        weight_table.metadata_json = metadata

        await self.db.commit()
        await self.db.refresh(weight_table)
        return weight_table
