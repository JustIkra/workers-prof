"""
Professional activities router.

Exposes read-only endpoints for available professional activity domains.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user, require_admin
from app.db.models import User
from app.db.session import get_db
from app.schemas.prof_activity import (
    ProfActivityCreateRequest,
    ProfActivityListResponse,
    ProfActivityResponse,
    ProfActivityUpdateRequest,
)
from app.services.prof_activity import ProfActivityService

router = APIRouter(prefix="/prof-activities", tags=["prof-activities"])


@router.get("", response_model=ProfActivityListResponse, status_code=status.HTTP_200_OK)
async def list_prof_activities(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> ProfActivityListResponse:
    """
    List all available professional activities.

    Requires:
        - Authenticated ACTIVE user
    """
    service = ProfActivityService(db)
    activities = await service.list_prof_activities()
    return ProfActivityListResponse(activities=activities)


@router.post("", response_model=ProfActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_prof_activity(
    request: ProfActivityCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> ProfActivityResponse:
    """
    Create a new professional activity.

    Requires:
        - ADMIN role
    """
    service = ProfActivityService(db)
    try:
        return await service.create_prof_activity(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put(
    "/{prof_activity_id}", response_model=ProfActivityResponse, status_code=status.HTTP_200_OK
)
async def update_prof_activity(
    prof_activity_id: UUID,
    request: ProfActivityUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> ProfActivityResponse:
    """
    Update a professional activity.

    Requires:
        - ADMIN role
    """
    service = ProfActivityService(db)
    try:
        return await service.update_prof_activity(prof_activity_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{prof_activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prof_activity(
    prof_activity_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    """
    Delete a professional activity.

    Requires:
        - ADMIN role

    Note: Will fail if there are weight tables associated with this activity.
    """
    service = ProfActivityService(db)
    try:
        await service.delete_prof_activity(prof_activity_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
