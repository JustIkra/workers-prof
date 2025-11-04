"""
Authentication service layer.

Handles password hashing, JWT token creation/validation, and user management.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import User


# ===== Password Hashing =====
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Args:
        password: Plaintext password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a hashed password.

    Args:
        plain_password: Plaintext password
        hashed_password: Hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


# ===== JWT Token Management =====
def create_access_token(user_id: uuid.UUID, email: str, role: str) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User UUID
        email: User email
        role: User role (ADMIN/USER)

    Returns:
        Encoded JWT token
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.access_token_ttl_min)

    payload = {
        "sub": str(user_id),  # Subject (user ID)
        "email": email,
        "role": role,
        "iat": now,  # Issued at
        "exp": expires_at,  # Expiration
    }

    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)
    return token


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload

    Raises:
        jwt.InvalidTokenError: If token is invalid or expired
    """
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
    return payload


# ===== User Repository Operations =====
async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """
    Get user by email address.

    Args:
        db: Database session
        email: User email

    Returns:
        User object or None if not found
    """
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """
    Get user by ID.

    Args:
        db: Database session
        user_id: User UUID

    Returns:
        User object or None if not found
    """
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, email: str, password: str, role: str = "USER") -> User:
    """
    Create a new user with PENDING status.

    Args:
        db: Database session
        email: User email
        password: Plaintext password (will be hashed)
        role: User role (default: USER)

    Returns:
        Created user object

    Raises:
        ValueError: If user with this email already exists
    """
    # Check if user already exists
    existing = await get_user_by_email(db, email)
    if existing:
        raise ValueError(f"User with email {email} already exists")

    # Create new user
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=hash_password(password),
        role=role,
        status="PENDING",
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """
    Authenticate user by email and password.

    Args:
        db: Database session
        email: User email
        password: Plaintext password

    Returns:
        User object if authentication successful, None otherwise
    """
    user = await get_user_by_email(db, email)

    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


async def approve_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    """
    Approve a pending user (change status to ACTIVE).

    Args:
        db: Database session
        user_id: User UUID to approve

    Returns:
        Updated user object

    Raises:
        ValueError: If user not found or already approved
    """
    user = await get_user_by_id(db, user_id)

    if not user:
        raise ValueError(f"User with ID {user_id} not found")

    if user.status == "ACTIVE":
        raise ValueError(f"User {user.email} is already active")

    if user.status == "DISABLED":
        raise ValueError(f"User {user.email} is disabled and cannot be approved")

    # Update status
    user.status = "ACTIVE"
    user.approved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(user)

    return user


async def list_pending_users(db: AsyncSession) -> list[User]:
    """
    List all users with PENDING status.

    Args:
        db: Database session

    Returns:
        List of pending users
    """
    result = await db.execute(select(User).where(User.status == "PENDING").order_by(User.created_at))
    return list(result.scalars().all())
