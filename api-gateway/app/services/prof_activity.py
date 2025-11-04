"""
Service layer for professional activities.

Provides list endpoint orchestration and seed helpers.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seeds import PROF_ACTIVITY_SEED_DATA
from app.repositories.prof_activity import ProfActivityRepository
from app.schemas.prof_activity import ProfActivityResponse


class ProfActivityService:
    """Business logic for professional activity operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProfActivityRepository(db)

    async def list_prof_activities(self) -> list[ProfActivityResponse]:
        """
        List all professional activities.

        Returns:
            List of serialized professional activities.
        """
        activities = await self.repo.list_all()
        return [ProfActivityResponse.model_validate(activity) for activity in activities]

    async def seed_defaults(self) -> None:
        """Seed default professional activities in idempotent manner."""
        await self.repo.seed_defaults(PROF_ACTIVITY_SEED_DATA)
