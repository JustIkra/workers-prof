"""
Repository layer for professional activities.

Provides read operations and idempotent seed insertion helpers.
"""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProfActivity
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
