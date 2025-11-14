"""
Service layer for Participant business logic.

Orchestrates participant operations with validation and error handling.
"""

from math import ceil
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.participant import ParticipantRepository
from app.schemas.participant import (
    ParticipantCreateRequest,
    ParticipantListResponse,
    ParticipantResponse,
    ParticipantSearchParams,
    ParticipantUpdateRequest,
)


class ParticipantService:
    """Service for participant business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ParticipantRepository(db)

    async def create_participant(self, request: ParticipantCreateRequest) -> ParticipantResponse:
        """
        Create a new participant.

        Args:
            request: Participant creation request

        Returns:
            Created participant response
        """
        participant = await self.repo.create(
            full_name=request.full_name,
            birth_date=request.birth_date,
            external_id=request.external_id,
        )
        return ParticipantResponse.model_validate(participant)

    async def get_participant(self, participant_id: UUID) -> ParticipantResponse | None:
        """
        Get a participant by ID.

        Args:
            participant_id: UUID of the participant

        Returns:
            Participant response if found, None otherwise
        """
        participant = await self.repo.get_by_id(participant_id)
        if not participant:
            return None
        return ParticipantResponse.model_validate(participant)

    async def update_participant(
        self, participant_id: UUID, request: ParticipantUpdateRequest
    ) -> ParticipantResponse | None:
        """
        Update a participant.

        Args:
            participant_id: UUID of the participant
            request: Update request with fields to change

        Returns:
            Updated participant response if found, None otherwise
        """
        # Only pass fields that are explicitly set
        participant = await self.repo.update(
            participant_id=participant_id,
            full_name=request.full_name,
            birth_date=request.birth_date,
            external_id=request.external_id,
        )
        if not participant:
            return None
        return ParticipantResponse.model_validate(participant)

    async def delete_participant(self, participant_id: UUID) -> bool:
        """
        Delete a participant.

        Args:
            participant_id: UUID of the participant

        Returns:
            True if deleted, False if not found
        """
        return await self.repo.delete(participant_id)

    async def search_participants(self, params: ParticipantSearchParams) -> ParticipantListResponse:
        """
        Search participants with pagination and filtering.

        Filters:
        - query: Case-insensitive substring search on full_name
        - external_id: Exact match on external_id

        Results are sorted deterministically by (full_name ASC, id ASC).

        Args:
            params: Search parameters (query, external_id, page, size)

        Returns:
            Paginated list of participants
        """
        participants, total = await self.repo.search(
            query=params.query,
            external_id=params.external_id,
            page=params.page,
            size=params.size,
        )

        # Convert to response DTOs
        items = [ParticipantResponse.model_validate(p) for p in participants]

        # Calculate total pages
        pages = ceil(total / params.size) if total > 0 else 0

        return ParticipantListResponse(
            items=items,
            total=total,
            page=params.page,
            size=params.size,
            pages=pages,
        )

    async def list_participants(self, page: int = 1, size: int = 20) -> ParticipantListResponse:
        """
        List all participants with pagination.

        Args:
            page: Page number (1-indexed)
            size: Page size

        Returns:
            Paginated list of all participants
        """
        params = ParticipantSearchParams(page=page, size=size)
        return await self.search_participants(params)
