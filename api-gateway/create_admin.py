"""
Create or update an ADMIN user.

Usage:
    python create_admin.py <email> [password]

If password is omitted, a secure random one is generated and printed.
If the user exists, role/status/password are updated to ADMIN/ACTIVE/new password.
"""

from __future__ import annotations

import asyncio
import secrets
import string
import sys
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.session import AsyncSessionLocal
from app.services.auth import get_user_by_email, hash_password


def _gen_password(length: int = 24) -> str:
    # bcrypt limit is 72 bytes; 24 chars is safe and strong
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()_-+="
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def _create_or_update_admin(email: str, password: str) -> tuple[User, bool]:
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        existing = await get_user_by_email(session, email)

        now = datetime.now(timezone.utc)
        password_hash = hash_password(password)

        if existing:
            existing.role = "ADMIN"
            existing.status = "ACTIVE"
            existing.approved_at = now
            existing.password_hash = password_hash
            await session.commit()
            await session.refresh(existing)
            return existing, False

        user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=password_hash,
            role="ADMIN",
            status="ACTIVE",
            approved_at=now,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user, True


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python create_admin.py <email> [password]", file=sys.stderr)
        return 2

    email = argv[1]
    password = argv[2] if len(argv) >= 3 else _gen_password()

    user, created = asyncio.run(_create_or_update_admin(email, password))

    action = "CREATED" if created else "UPDATED"
    print("=== ADMIN", action, "===")
    print("id:", user.id)
    print("email:", user.email)
    print("password:", password)
    print("status:", user.status)
    print("role:", user.role)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

