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

        Returns newest versions first within each activity.
        """
        stmt = (
            select(WeightTable)
            .options(selectinload(WeightTable.prof_activity))
            .order_by(WeightTable.prof_activity_id, WeightTable.version.desc())
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

    async def get_active_for_activity(
        self,
        prof_activity_id: uuid.UUID,
        exclude_id: uuid.UUID | None = None,
    ) -> WeightTable | None:
        """
        Get currently active weight table for given professional activity.

        Optionally exclude a specific weight table ID.
        """
        stmt = (
            select(WeightTable)
            .options(selectinload(WeightTable.prof_activity))
            .where(
                WeightTable.prof_activity_id == prof_activity_id,
                WeightTable.is_active.is_(True),
            )
        )

        if exclude_id:
            stmt = stmt.where(WeightTable.id != exclude_id)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_next_version(self, prof_activity_id: uuid.UUID) -> int:
        """Determine the next version number for a professional activity."""
        stmt = select(func.max(WeightTable.version)).where(
            WeightTable.prof_activity_id == prof_activity_id
        )
        result = await self.db.execute(stmt)
        current_max = result.scalar_one()
        if current_max is None:
            return 1
        return int(current_max) + 1

    async def create(
        self,
        prof_activity_id: uuid.UUID,
        version: int,
        weights: list[dict[str, Any]],
        metadata: dict[str, Any] | None,
    ) -> WeightTable:
        """Create and persist a new weight table."""
        weight_table = WeightTable(
            id=uuid.uuid4(),
            prof_activity_id=prof_activity_id,
            version=version,
            weights=weights,
            metadata_json=metadata,
            is_active=False,
        )

        self.db.add(weight_table)
        await self.db.commit()
        await self.db.refresh(weight_table)
        return weight_table

    async def activate(self, weight_table: WeightTable) -> WeightTable:
        """Mark given weight table as active."""
        weight_table.is_active = True
        await self.db.flush()  # Ensure change is written to DB before commit
        await self.db.commit()
        await self.db.refresh(weight_table)
        return weight_table
