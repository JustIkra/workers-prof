"""
Tests for weight table endpoints.

Validates:
- Successful upload of weight table JSON
- Validation failure when weights do not sum to 1.0
- Update existing weight table
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProfActivity, User, WeightTable
from app.services.auth import create_user
from app.services.prof_activity import ProfActivityService


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create and activate an admin user for weight management."""
    user = await create_user(
        db_session,
        email="weight_admin@example.com",
        password="securepassword1",
        role="ADMIN",
    )
    user.status = "ACTIVE"
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_cookies(
    client: AsyncClient,
    admin_user: User,
) -> dict[str, str]:
    """Authenticate admin user and return JWT cookies."""
    response = await client.post(
        "/api/auth/login",
        json={"email": "weight_admin@example.com", "password": "securepassword1"},
    )
    assert response.status_code == 200
    cookies = dict(response.cookies)
    client.cookies.clear()
    return cookies


@pytest.fixture
async def prof_activity_seeded(db_session: AsyncSession) -> None:
    """Ensure professional activities are populated."""
    service = ProfActivityService(db_session)
    await service.seed_defaults()


@pytest.mark.asyncio
async def test_upload_weight_table_success(
    test_env,
    client: AsyncClient,
    db_session: AsyncSession,
    admin_cookies: dict[str, str],
    prof_activity_seeded: None,
):
    """Uploading a valid weight table creates a new version."""
    payload = {
        "prof_activity_code": "meeting_facilitation",
        "weights": [
            {"metric_code": "agenda_preparation", "weight": "0.4"},
            {"metric_code": "moderation", "weight": "0.3"},
            {"metric_code": "follow_up", "weight": "0.3"},
        ],
        "metadata": {"source": "unit-test"},
    }

    response = await client.post(
        "/api/admin/weights/upload",
        json=payload,
        cookies=admin_cookies,
    )

    if response.status_code != 201:
        print(f"Error response: {response.json()}")
    assert response.status_code == 201
    data = response.json()

    assert data["prof_activity_code"] == "meeting_facilitation"
    assert data["metadata"] == {"source": "unit-test"}
    assert [entry["metric_code"] for entry in data["weights"]] == [
        "agenda_preparation",
        "moderation",
        "follow_up",
    ]

    # Ensure persisted in database
    result = await db_session.execute(select(WeightTable))
    tables = list(result.scalars().all())
    assert len(tables) == 1


@pytest.mark.asyncio
async def test_upload_weight_table_invalid_sum_rejected(
    test_env,
    client: AsyncClient,
    admin_cookies: dict[str, str],
    prof_activity_seeded: None,
):
    """Weights not summing to 1.0 trigger validation error."""
    payload = {
        "prof_activity_code": "meeting_facilitation",
        "weights": [
            {"metric_code": "agenda_preparation", "weight": "0.6"},
            {"metric_code": "moderation", "weight": "0.3"},
        ],
    }

    response = await client.post(
        "/api/admin/weights/upload",
        json=payload,
        cookies=admin_cookies,
    )

    assert response.status_code == 422
    assert any(
        "Sum of weights must equal 1.0" in error["msg"] for error in response.json()["detail"]
    )


@pytest.mark.asyncio
async def test_update_existing_weight_table(
    test_env,
    client: AsyncClient,
    db_session: AsyncSession,
    admin_cookies: dict[str, str],
    prof_activity_seeded: None,
):
    """Updating an existing weight table replaces its weights."""
    # Create initial table
    payload_v1 = {
        "prof_activity_code": "meeting_facilitation",
        "weights": [
            {"metric_code": "agenda_preparation", "weight": "0.5"},
            {"metric_code": "moderation", "weight": "0.5"},
        ],
    }

    resp_v1 = await client.post(
        "/api/admin/weights/upload",
        json=payload_v1,
        cookies=admin_cookies,
    )
    assert resp_v1.status_code == 201
    table_id = resp_v1.json()["id"]

    # Update the table with new weights
    payload_v2 = {
        "prof_activity_code": "meeting_facilitation",
        "weights": [
            {"metric_code": "agenda_preparation", "weight": "0.2"},
            {"metric_code": "moderation", "weight": "0.3"},
            {"metric_code": "follow_up", "weight": "0.5"},
        ],
    }

    update_resp = await client.put(
        f"/api/admin/weights/{table_id}",
        json=payload_v2,
        cookies=admin_cookies,
    )
    assert update_resp.status_code == 200
    updated_data = update_resp.json()

    # Verify weights were updated
    assert len(updated_data["weights"]) == 3
    assert [entry["metric_code"] for entry in updated_data["weights"]] == [
        "agenda_preparation",
        "moderation",
        "follow_up",
    ]

    # Confirm DB still has only one table for this activity
    result = await db_session.execute(
        select(WeightTable).join(ProfActivity).where(ProfActivity.code == "meeting_facilitation")
    )
    tables = list(result.scalars().all())
    assert len(tables) == 1
    assert len(tables[0].weights) == 3
