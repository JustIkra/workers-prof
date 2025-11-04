"""
Professional activities router.

Exposes read-only endpoints for available professional activity domains.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.prof_activity import ProfActivityResponse
from app.services.prof_activity import ProfActivityService

router = APIRouter(prefix="/prof-activities", tags=["prof-activities"])


@router.get("", response_model=list[ProfActivityResponse], status_code=status.HTTP_200_OK)
async def list_prof_activities(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> list[ProfActivityResponse]:
    """
    List all available professional activities.

    Requires:
        - Authenticated ACTIVE user
    """
    service = ProfActivityService(db)
    return await service.list_prof_activities()
