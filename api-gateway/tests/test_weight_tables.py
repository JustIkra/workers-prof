"""
Tests for weight table endpoints.

Validates:
- Successful upload of weight table JSON with versioning
- Validation failure when weights do not sum to 1.0
- Activation guard preventing multiple active versions per activity
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProfActivity, WeightTable, User
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
    return dict(response.cookies)


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

    assert response.status_code == 201
    data = response.json()

    assert data["prof_activity_code"] == "meeting_facilitation"
    assert data["version"] == 1
    assert data["is_active"] is False
    assert data["metadata"] == {"source": "unit-test"}
    assert [entry["metric_code"] for entry in data["weights"]] == [
        "agenda_preparation",
        "moderation",
        "follow_up",
    ]

    # Ensure persisted in database with version 1
    result = await db_session.execute(select(WeightTable))
    tables = list(result.scalars().all())
    assert len(tables) == 1
    assert tables[0].version == 1


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
        "Sum of weights must equal 1.0" in error["msg"]
        for error in response.json()["detail"]
    )


@pytest.mark.asyncio
async def test_activate_second_weight_table_rejected(
    test_env,
    client: AsyncClient,
    db_session: AsyncSession,
    admin_cookies: dict[str, str],
    prof_activity_seeded: None,
):
    """Activating a second table while another is active is rejected."""
    # Upload two versions
    payload_v1 = {
        "prof_activity_code": "meeting_facilitation",
        "weights": [
            {"metric_code": "agenda_preparation", "weight": "0.5"},
            {"metric_code": "moderation", "weight": "0.5"},
        ],
    }
    payload_v2 = {
        "prof_activity_code": "meeting_facilitation",
        "weights": [
            {"metric_code": "agenda_preparation", "weight": "0.2"},
            {"metric_code": "moderation", "weight": "0.3"},
            {"metric_code": "follow_up", "weight": "0.5"},
        ],
    }

    resp_v1 = await client.post(
        "/api/admin/weights/upload",
        json=payload_v1,
        cookies=admin_cookies,
    )
    assert resp_v1.status_code == 201
    resp_v2 = await client.post(
        "/api/admin/weights/upload",
        json=payload_v2,
        cookies=admin_cookies,
    )
    assert resp_v2.status_code == 201

    id_v1 = resp_v1.json()["id"]
    id_v2 = resp_v2.json()["id"]

    # Activate first table
    activate_resp = await client.post(
        f"/api/admin/weights/{id_v1}/activate",
        cookies=admin_cookies,
    )
    assert activate_resp.status_code == 200
    assert activate_resp.json()["is_active"] is True

    # Attempt to activate second while first is still active
    conflict_resp = await client.post(
        f"/api/admin/weights/{id_v2}/activate",
        cookies=admin_cookies,
    )
    assert conflict_resp.status_code == 400
    assert "another active weight table" in conflict_resp.json()["detail"].lower()

    # Confirm DB still has single active record
    result = await db_session.execute(
        select(WeightTable)
        .join(ProfActivity)
        .where(ProfActivity.code == "meeting_facilitation")
    )
    tables = list(result.scalars().all())
    assert any(table.is_active for table in tables)
    assert sum(1 for table in tables if table.is_active) == 1
