"""
Tests for professional activities seeding and API listing.

Covers:
- Idempotent seeding of default professional activities
- Authenticated retrieval via GET /api/prof-activities
- Authentication enforcement
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProfActivity, User
from app.db.seeds.prof_activity import PROF_ACTIVITY_SEED_DATA
from app.services.auth import create_user
from app.services.prof_activity import ProfActivityService

# ===== Helper Fixtures =====


@pytest.fixture
async def active_user(db_session: AsyncSession) -> User:
    """Create an active user to access protected endpoints."""
    user = await create_user(db_session, "activity_user@example.com", "password123", role="USER")
    user.status = "ACTIVE"
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def auth_cookies(client: AsyncClient, active_user: User) -> dict[str, str]:
    """Authenticate the active user and return JWT cookies."""
    response = await client.post(
        "/api/auth/login",
        json={"email": "activity_user@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    cookies = dict(response.cookies)
    client.cookies.clear()
    return cookies


@pytest.fixture
async def seeded_prof_activities(db_session: AsyncSession) -> None:
    """Ensure default professional activities are present."""
    service = ProfActivityService(db_session)
    await service.seed_defaults()


# ===== Tests =====


@pytest.mark.asyncio
async def test_seed_prof_activities__idempotent(test_env, db_session: AsyncSession):
    """Running the seeder twice keeps a single copy with consistent data."""
    service = ProfActivityService(db_session)

    await service.seed_defaults()
    first_result = await db_session.execute(select(ProfActivity))
    first_items = list(first_result.scalars().all())

    await service.seed_defaults()
    second_result = await db_session.execute(select(ProfActivity))
    second_items = list(second_result.scalars().all())

    assert len(first_items) == len(PROF_ACTIVITY_SEED_DATA)
    assert len(second_items) == len(PROF_ACTIVITY_SEED_DATA)

    for seed in PROF_ACTIVITY_SEED_DATA:
        match = next((item for item in second_items if item.code == seed.code), None)
        assert match is not None
        assert match.name == seed.name
        assert match.description == seed.description


@pytest.mark.asyncio
async def test_list_prof_activities__returns_seeded_items(
    test_env,
    client: AsyncClient,
    db_session: AsyncSession,
    auth_cookies: dict[str, str],
    seeded_prof_activities: None,
):
    """Listing endpoint returns seeded professional activities."""
    response = await client.get("/api/prof-activities", cookies=auth_cookies)

    assert response.status_code == 200
    data = response.json()

    assert len(data) == len(PROF_ACTIVITY_SEED_DATA)

    expected = {seed.code: seed for seed in PROF_ACTIVITY_SEED_DATA}
    for item in data:
        seed = expected[item["code"]]
        assert item["name"] == seed.name
        assert item["description"] == seed.description


@pytest.mark.asyncio
async def test_list_prof_activities__no_auth__returns_401(
    test_env,
    client: AsyncClient,
    db_session: AsyncSession,
    seeded_prof_activities: None,
):
    """Listing endpoint requires authentication."""
    response = await client.get("/api/prof-activities")

    assert response.status_code == 401
