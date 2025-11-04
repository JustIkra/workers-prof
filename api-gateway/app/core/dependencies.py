"""
FastAPI dependencies for authentication and authorization.

Provides dependency functions for getting current user and checking roles.
"""

import uuid

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.session import get_db
from app.services.auth import decode_access_token, get_user_by_id


async def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token in cookie.

    Args:
        access_token: JWT token from httpOnly cookie
        db: Database session

    Returns:
        Current user object

    Raises:
        HTTPException: 401 if token is missing, invalid, or user not found
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in.",
        )

    try:
        payload = decode_access_token(access_token)
        user_id_str = payload.get("sub")

        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
            )

        user_id = uuid.UUID(user_id_str)

    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: malformed user ID",
        )

    # Get user from database
    user = await get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current user and ensure they are ACTIVE.

    Args:
        current_user: Current user from get_current_user

    Returns:
        Current active user

    Raises:
        HTTPException: 403 if user is not active
    """
    if current_user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account is {current_user.status}. Please contact an administrator.",
        )

    return current_user


async def require_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Require current user to be an ACTIVE ADMIN.

    Args:
        current_user: Current active user

    Returns:
        Current admin user

    Raises:
        HTTPException: 403 if user is not an admin
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )

    return current_user


# ===== Optional User (for endpoints that work with or without auth) =====
async def get_current_user_optional(
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Get current user if authenticated, None otherwise.

    Args:
        access_token: JWT token from httpOnly cookie
        db: Database session

    Returns:
        Current user object or None
    """
    if not access_token:
        return None

    try:
        payload = decode_access_token(access_token)
        user_id_str = payload.get("sub")

        if not user_id_str:
            return None

        user_id = uuid.UUID(user_id_str)
        user = await get_user_by_id(db, user_id)
        return user

    except (jwt.InvalidTokenError, ValueError):
        return None
