"""
Admin router.

Administrative endpoints for user management.
Requires ADMIN role for all operations.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import MessageResponse, UserResponse
from app.services.auth import approve_user, list_pending_users

router = APIRouter()


@router.get("/pending-users", response_model=list[UserResponse])
async def get_pending_users(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """
    List all users with PENDING status awaiting approval.

    **Requires:** ADMIN role

    **Returns:** List of pending users ordered by registration date

    **Errors:**
    - 401: Not authenticated
    - 403: Not an admin
    """
    users = await list_pending_users(db)
    return [UserResponse.model_validate(user) for user in users]


@router.post("/approve/{user_id}", response_model=UserResponse)
async def approve_user_endpoint(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """
    Approve a pending user (change status to ACTIVE).

    **Requires:** ADMIN role

    **Flow:**
    1. Admin views pending users via `/admin/pending-users`
    2. Admin approves a user by their UUID
    3. User status changes from PENDING → ACTIVE
    4. User can now log in and access the system

    **Errors:**
    - 400: User not found, already approved, or disabled
    - 401: Not authenticated
    - 403: Not an admin
    """
    try:
        user = await approve_user(db, user_id)
        return UserResponse.model_validate(user)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
