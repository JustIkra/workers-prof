"""
Repository layer for Participant data access.

Handles all database operations for participants with proper sorting and filtering.
"""

from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Participant

# PostgreSQL running with default C locale does not downcase Cyrillic characters when using ILIKE.
# We normalize case via translate() so substring searches behave consistently for Cyrillic and Latin.
CASEFOLD_TRANSLATE_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
CASEFOLD_TRANSLATE_LOWER = "abcdefghijklmnopqrstuvwxyzабвгдеёжзийклмнопрстуфхцчшщъыьэюя"

class ParticipantRepository:
    """Repository for participant database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, full_name: str, birth_date: Optional[date] = None, external_id: Optional[str] = None
    ) -> Participant:
        """
        Create a new participant.

        Args:
            full_name: Full name of the participant
            birth_date: Optional birth date
            external_id: Optional external ID

        Returns:
            Created Participant instance
        """
        participant = Participant(full_name=full_name, birth_date=birth_date, external_id=external_id)
        self.db.add(participant)
        await self.db.commit()
        await self.db.refresh(participant)
        return participant

    async def get_by_id(self, participant_id: UUID) -> Optional[Participant]:
        """
        Get a participant by ID.

        Args:
            participant_id: UUID of the participant

        Returns:
            Participant if found, None otherwise
        """
        result = await self.db.execute(select(Participant).where(Participant.id == participant_id))
        return result.scalar_one_or_none()

    async def update(
        self,
        participant_id: UUID,
        full_name: Optional[str] = None,
        birth_date: Optional[date] = None,
        external_id: Optional[str] = None,
    ) -> Optional[Participant]:
        """
        Update a participant.

        Args:
            participant_id: UUID of the participant
            full_name: New full name (if provided)
            birth_date: New birth date (if provided)
            external_id: New external ID (if provided)

        Returns:
            Updated Participant if found, None otherwise
        """
        participant = await self.get_by_id(participant_id)
        if not participant:
            return None

        if full_name is not None:
            participant.full_name = full_name
        if birth_date is not None:
            participant.birth_date = birth_date
        if external_id is not None:
            participant.external_id = external_id

        await self.db.commit()
        await self.db.refresh(participant)
        return participant

    async def delete(self, participant_id: UUID) -> bool:
        """
        Delete a participant.

        Args:
            participant_id: UUID of the participant

        Returns:
            True if deleted, False if not found
        """
        participant = await self.get_by_id(participant_id)
        if not participant:
            return False

        await self.db.delete(participant)
        await self.db.commit()
        return True

    async def search(
        self,
        query: Optional[str] = None,
        external_id: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Participant], int]:
        """
        Search participants with pagination and deterministic sorting.

        Filters:
        - query: Case-insensitive substring search on full_name
        - external_id: Exact match on external_id

        Sorting: Always by (full_name ASC, id ASC) for determinism when full_name duplicates exist.

        Args:
            query: Search string for full_name (case-insensitive substring)
            external_id: Exact match for external_id
            page: Page number (1-indexed)
            size: Page size

        Returns:
            Tuple of (list of participants, total count)
        """
        # Build base query
        stmt = select(Participant)

        # Apply filters
        filters = []

        # Prepare normalized full_name expression once to reuse across filters.
        normalized_full_name = func.translate(
            Participant.full_name,
            CASEFOLD_TRANSLATE_UPPER,
            CASEFOLD_TRANSLATE_LOWER,
        )

        if query:
            normalized_query = query.casefold()
            filters.append(normalized_full_name.like(f"%{normalized_query}%"))
        if external_id:
            # Exact match
            filters.append(Participant.external_id == external_id)

        if filters:
            stmt = stmt.where(or_(*filters) if len(filters) > 1 else filters[0])

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        # Apply deterministic sorting: full_name ASC, id ASC
        stmt = stmt.order_by(Participant.full_name, Participant.id)

        # Apply pagination
        offset = (page - 1) * size
        stmt = stmt.offset(offset).limit(size)

        # Execute query
        result = await self.db.execute(stmt)
        participants = list(result.scalars().all())

        return participants, total

    async def list_all(self, page: int = 1, size: int = 20) -> tuple[list[Participant], int]:
        """
        List all participants with pagination.

        Args:
            page: Page number (1-indexed)
            size: Page size

        Returns:
            Tuple of (list of participants, total count)
        """
        return await self.search(query=None, external_id=None, page=page, size=size)
