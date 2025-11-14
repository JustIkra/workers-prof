"""
Repository layer for professional activities.

Provides read operations and idempotent seed insertion helpers.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProfActivity, WeightTable
from app.db.seeds.prof_activity import ProfActivitySeed


class ProfActivityRepository:
    """Repository for prof_activity table interactions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self) -> list[ProfActivity]:
        """
        Retrieve all professional activities sorted by code.

        Returns:
            List of ProfActivity rows ordered deterministically.
        """
        stmt = select(ProfActivity).order_by(ProfActivity.code, ProfActivity.id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_code(self, code: str) -> ProfActivity | None:
        """
        Retrieve a professional activity by its unique code.

        Args:
            code: Activity code to search for

        Returns:
            ProfActivity instance or None if not found.
        """
        stmt = select(ProfActivity).where(ProfActivity.code == code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_weight_table(self, prof_activity_id: UUID) -> WeightTable | None:
        """
        Get the weight table for a professional activity.

        Note: After migration d952812cd1d6, there is one weight table per activity (no versioning).

        Args:
            prof_activity_id: UUID of the professional activity

        Returns:
            WeightTable instance or None if not found.
        """
        stmt = select(WeightTable).where(WeightTable.prof_activity_id == prof_activity_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, code: str, name: str, description: str | None = None) -> ProfActivity:
        """
        Create a new professional activity.

        Args:
            code: Unique activity code
            name: Activity name
            description: Optional description

        Returns:
            Created ProfActivity instance
        """
        prof_activity = ProfActivity(code=code, name=name, description=description)
        self.db.add(prof_activity)
        await self.db.commit()
        await self.db.refresh(prof_activity)
        return prof_activity

    async def update(
        self, prof_activity_id: UUID, name: str | None = None, description: str | None = None
    ) -> ProfActivity | None:
        """
        Update a professional activity.

        Args:
            prof_activity_id: UUID of the activity to update
            name: Optional new name
            description: Optional new description

        Returns:
            Updated ProfActivity instance or None if not found
        """
        stmt = select(ProfActivity).where(ProfActivity.id == prof_activity_id)
        result = await self.db.execute(stmt)
        prof_activity = result.scalar_one_or_none()

        if not prof_activity:
            return None

        if name is not None:
            prof_activity.name = name
        if description is not None:
            prof_activity.description = description

        await self.db.commit()
        await self.db.refresh(prof_activity)
        return prof_activity

    async def delete(self, prof_activity_id: UUID) -> bool:
        """
        Delete a professional activity.

        Args:
            prof_activity_id: UUID of the activity to delete

        Returns:
            True if deleted, False if not found
        """
        stmt = select(ProfActivity).where(ProfActivity.id == prof_activity_id)
        result = await self.db.execute(stmt)
        prof_activity = result.scalar_one_or_none()

        if not prof_activity:
            return False

        await self.db.delete(prof_activity)
        await self.db.commit()
        return True

    async def seed_defaults(self, seeds: Sequence[ProfActivitySeed]) -> None:
        """
        Upsert default professional activities.

        Each seed is inserted once and subsequent runs update name/description only.
        """
        for seed in seeds:
            stmt = (
                insert(ProfActivity)
                .values(
                    id=seed.id,
                    code=seed.code,
                    name=seed.name,
                    description=seed.description,
                )
                .on_conflict_do_update(
                    index_elements=[ProfActivity.code],
                    set_={
                        "name": seed.name,
                        "description": seed.description,
                    },
                )
            )
            await self.db.execute(stmt)

        await self.db.commit()
