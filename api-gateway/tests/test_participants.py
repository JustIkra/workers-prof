"""
Comprehensive tests for participant CRUD and search endpoints.

Tests cover:
- Create participant (POST /api/participants)
- Get participant by ID (GET /api/participants/{id})
- Update participant (PUT /api/participants/{id})
- Delete participant (DELETE /api/participants/{id})
- Search participants with pagination (GET /api/participants)
- Deterministic sorting (full_name, id)
- Authentication requirements
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Participant, User
from app.services.auth import create_user


# ===== Helper Fixtures =====


@pytest.fixture
async def active_user(db_session: AsyncSession) -> User:
    """Create an active user for authenticated requests."""
    user = await create_user(db_session, "active@example.com", "password123", role="USER")
    user.status = "ACTIVE"
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def auth_cookies(client: AsyncClient, active_user: User) -> dict:
    """Get authentication cookies for active user."""
    # Login to get JWT cookie
    response = await client.post(
        "/api/auth/login",
        json={"email": "active@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    cookies = dict(response.cookies)
    # Clear shared client cookie jar so tests explicitly control auth state.
    client.cookies.clear()
    return cookies


@pytest.fixture
async def sample_participant(db_session: AsyncSession) -> Participant:
    """Create a sample participant for tests."""
    participant = Participant(
        full_name="Иван Иванов",
        birth_date=date(1990, 1, 15),
        external_id="EXT001",
    )
    db_session.add(participant)
    await db_session.commit()
    await db_session.refresh(participant)
    return participant


# ===== Create Participant Tests =====


@pytest.mark.asyncio
async def test_create_participant__valid__returns_201(
    test_env, client: AsyncClient, auth_cookies: dict
):
    """Test successful participant creation."""
    response = await client.post(
        "/api/participants",
        json={
            "full_name": "Иван Петров",
            "birth_date": "1995-03-20",
            "external_id": "EXT123",
        },
        cookies=auth_cookies,
    )

    assert response.status_code == 201
    data = response.json()

    assert data["full_name"] == "Иван Петров"
    assert data["birth_date"] == "1995-03-20"
    assert data["external_id"] == "EXT123"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_participant__minimal_fields__returns_201(
    test_env, client: AsyncClient, auth_cookies: dict
):
    """Test participant creation with only required field (full_name)."""
    response = await client.post(
        "/api/participants",
        json={"full_name": "Мария Сидорова"}, cookies=auth_cookies)

    assert response.status_code == 201
    data = response.json()

    assert data["full_name"] == "Мария Сидорова"
    assert data["birth_date"] is None
    assert data["external_id"] is None


@pytest.mark.asyncio
async def test_create_participant__empty_name__returns_422(
    test_env, client: AsyncClient, auth_cookies: dict
):
    """Test participant creation with empty full_name returns 422."""
    response = await client.post(
        "/api/participants",
        json={"full_name": ""}, cookies=auth_cookies)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_participant__no_auth__returns_401(test_env, client: AsyncClient):
    """Test participant creation without authentication returns 401."""
    response = await client.post(
        "/api/participants",
        json={"full_name": "Петр Петров"})

    assert response.status_code == 401


# ===== Get Participant Tests =====


@pytest.mark.asyncio
async def test_get_participant__exists__returns_200(
    test_env, client: AsyncClient, auth_cookies: dict, sample_participant: Participant
):
    """Test getting an existing participant returns 200."""
    response = await client.get(f"/api/participants/{sample_participant.id}", cookies=auth_cookies)

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == str(sample_participant.id)
    assert data["full_name"] == sample_participant.full_name
    assert data["birth_date"] == sample_participant.birth_date.isoformat()
    assert data["external_id"] == sample_participant.external_id


@pytest.mark.asyncio
async def test_get_participant__not_exists__returns_404(
    test_env, client: AsyncClient, auth_cookies: dict
):
    """Test getting non-existent participant returns 404."""
    fake_id = uuid.uuid4()
    response = await client.get(f"/api/participants/{fake_id}", cookies=auth_cookies)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_participant__no_auth__returns_401(
    test_env, client: AsyncClient, sample_participant: Participant
):
    """Test getting participant without authentication returns 401."""
    response = await client.get(f"/api/participants/{sample_participant.id}")

    assert response.status_code == 401


# ===== Update Participant Tests =====


@pytest.mark.asyncio
async def test_update_participant__full_name__returns_200(
    test_env, client: AsyncClient, auth_cookies: dict, sample_participant: Participant
):
    """Test updating participant full_name."""
    response = await client.put(
        f"/api/participants/{sample_participant.id}",
        json={"full_name": "Иванов Иван Иванович"}, cookies=auth_cookies)

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == str(sample_participant.id)
    assert data["full_name"] == "Иванов Иван Иванович"
    # Other fields unchanged
    assert data["birth_date"] == sample_participant.birth_date.isoformat()
    assert data["external_id"] == sample_participant.external_id


@pytest.mark.asyncio
async def test_update_participant__multiple_fields__returns_200(
    test_env, client: AsyncClient, auth_cookies: dict, sample_participant: Participant
):
    """Test updating multiple participant fields."""
    response = await client.put(
        f"/api/participants/{sample_participant.id}",
        json={
            "full_name": "Новое Имя",
            "birth_date": "1992-05-10",
            "external_id": "NEWEXT",
        }, cookies=auth_cookies)

    assert response.status_code == 200
    data = response.json()

    assert data["full_name"] == "Новое Имя"
    assert data["birth_date"] == "1992-05-10"
    assert data["external_id"] == "NEWEXT"


@pytest.mark.asyncio
async def test_update_participant__not_exists__returns_404(
    test_env, client: AsyncClient, auth_cookies: dict
):
    """Test updating non-existent participant returns 404."""
    fake_id = uuid.uuid4()
    response = await client.put(
        f"/api/participants/{fake_id}",
        json={"full_name": "New Name"}, cookies=auth_cookies)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_participant__no_auth__returns_401(
    test_env, client: AsyncClient, sample_participant: Participant
):
    """Test updating participant without authentication returns 401."""
    response = await client.put(
        f"/api/participants/{sample_participant.id}",
        json={"full_name": "New Name"})

    assert response.status_code == 401


# ===== Delete Participant Tests =====


@pytest.mark.asyncio
async def test_delete_participant__exists__returns_200(
    test_env, client: AsyncClient, auth_cookies: dict, sample_participant: Participant, db_session: AsyncSession
):
    """Test deleting an existing participant."""
    response = await client.delete(f"/api/participants/{sample_participant.id}", cookies=auth_cookies)

    assert response.status_code == 200
    assert "deleted" in response.json()["message"].lower()

    # Verify participant is deleted from database
    from sqlalchemy import select
    result = await db_session.execute(
        select(Participant).where(Participant.id == sample_participant.id)
    )
    deleted_participant = result.scalar_one_or_none()
    assert deleted_participant is None


@pytest.mark.asyncio
async def test_delete_participant__not_exists__returns_404(
    test_env, client: AsyncClient, auth_cookies: dict
):
    """Test deleting non-existent participant returns 404."""
    fake_id = uuid.uuid4()
    response = await client.delete(f"/api/participants/{fake_id}", cookies=auth_cookies)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_participant__no_auth__returns_401(
    test_env, client: AsyncClient, sample_participant: Participant
):
    """Test deleting participant without authentication returns 401."""
    response = await client.delete(f"/api/participants/{sample_participant.id}")

    assert response.status_code == 401


# ===== Search/List Participants Tests =====


@pytest.mark.asyncio
async def test_list_participants__empty__returns_empty_list(
    test_env, client: AsyncClient, auth_cookies: dict
):
    """Test listing participants when none exist."""
    response = await client.get("/api/participants", cookies=auth_cookies)

    assert response.status_code == 200
    data = response.json()

    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["size"] == 20
    assert data["pages"] == 0


@pytest.mark.asyncio
async def test_list_participants__multiple__returns_sorted_list(
    test_env, client: AsyncClient, auth_cookies: dict, db_session: AsyncSession
):
    """Test listing multiple participants with deterministic sorting."""
    # Create participants with different names
    participants_data = [
        ("Яков Петров", "EXT003"),
        ("Анна Иванова", "EXT001"),
        ("Борис Сидоров", "EXT002"),
        ("Анна Петрова", "EXT004"),  # Same first name as first, different last name
    ]

    for full_name, external_id in participants_data:
        p = Participant(full_name=full_name, external_id=external_id)
        db_session.add(p)
    await db_session.commit()

    response = await client.get("/api/participants", cookies=auth_cookies)

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 4
    assert len(data["items"]) == 4

    # Verify deterministic sorting: full_name ASC, id ASC
    names = [item["full_name"] for item in data["items"]]
    assert names == ["Анна Иванова", "Анна Петрова", "Борис Сидоров", "Яков Петров"]


@pytest.mark.asyncio
async def test_list_participants__pagination__returns_correct_page(
    test_env, client: AsyncClient, auth_cookies: dict, db_session: AsyncSession
):
    """Test pagination with page and size parameters."""
    # Create 25 participants
    for i in range(25):
        p = Participant(full_name=f"Участник {i:02d}", external_id=f"EXT{i:03d}")
        db_session.add(p)
    await db_session.commit()

    # Get page 1 with size 10
    response = await client.get("/api/participants?page=1&size=10", cookies=auth_cookies)
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 25
    assert data["page"] == 1
    assert data["size"] == 10
    assert data["pages"] == 3
    assert len(data["items"]) == 10

    # Get page 2 with size 10
    response = await client.get("/api/participants?page=2&size=10", cookies=auth_cookies)
    data = response.json()

    assert data["page"] == 2
    assert len(data["items"]) == 10

    # Get page 3 with size 10 (last page with 5 items)
    response = await client.get("/api/participants?page=3&size=10", cookies=auth_cookies)
    data = response.json()

    assert data["page"] == 3
    assert len(data["items"]) == 5


@pytest.mark.asyncio
async def test_search_participants__by_query__returns_matching(
    test_env, client: AsyncClient, auth_cookies: dict, db_session: AsyncSession
):
    """Test searching participants by full_name substring (case-insensitive)."""
    participants_data = [
        "Иван Иванов",
        "Петр Петров",
        "Иванна Сидорова",
        "Сидор Иванович",
    ]

    for full_name in participants_data:
        p = Participant(full_name=full_name)
        db_session.add(p)
    await db_session.commit()

    # Search for "иван" (case-insensitive)
    response = await client.get("/api/participants?query=иван", cookies=auth_cookies)

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 3  # Иван Иванов, Иванна Сидорова, Сидор Иванович
    names = [item["full_name"] for item in data["items"]]
    assert "Иван Иванов" in names
    assert "Иванна Сидорова" in names
    assert "Сидор Иванович" in names


@pytest.mark.asyncio
async def test_search_participants__by_external_id__returns_exact_match(
    test_env, client: AsyncClient, auth_cookies: dict, db_session: AsyncSession
):
    """Test filtering by exact external_id match."""
    participants_data = [
        ("Иван Иванов", "EXT001"),
        ("Петр Петров", "EXT002"),
        ("Сидор Сидоров", "EXT001A"),  # Similar but not exact match
    ]

    for full_name, external_id in participants_data:
        p = Participant(full_name=full_name, external_id=external_id)
        db_session.add(p)
    await db_session.commit()

    # Search for exact external_id "EXT001"
    response = await client.get("/api/participants?external_id=EXT001", cookies=auth_cookies)

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["full_name"] == "Иван Иванов"
    assert data["items"][0]["external_id"] == "EXT001"


@pytest.mark.asyncio
async def test_search_participants__combined_filters__returns_matching(
    test_env, client: AsyncClient, auth_cookies: dict, db_session: AsyncSession
):
    """Test combined query and external_id filters."""
    participants_data = [
        ("Иван Иванов", "EXT001"),
        ("Иван Петров", "EXT002"),
        ("Петр Иванов", "EXT001"),
    ]

    for full_name, external_id in participants_data:
        p = Participant(full_name=full_name, external_id=external_id)
        db_session.add(p)
    await db_session.commit()

    # Search for "иван" OR external_id "EXT001"
    response = await client.get("/api/participants?query=иван&external_id=EXT001", cookies=auth_cookies)

    assert response.status_code == 200
    data = response.json()

    # Should return all 3 (OR condition in repository)
    assert data["total"] == 3


@pytest.mark.asyncio
async def test_search_participants__deterministic_with_duplicate_names(
    test_env, client: AsyncClient, auth_cookies: dict, db_session: AsyncSession
):
    """Test deterministic sorting when multiple participants have same full_name."""
    # Create 3 participants with same name
    for i in range(3):
        p = Participant(full_name="Иван Иванов", external_id=f"EXT{i:03d}")
        db_session.add(p)
    await db_session.commit()

    # Fetch twice and compare order
    response1 = await client.get("/api/participants?query=иван", cookies=auth_cookies)
    data1 = response1.json()

    response2 = await client.get("/api/participants?query=иван", cookies=auth_cookies)
    data2 = response2.json()

    # Order should be identical (sorted by id as secondary)
    ids1 = [item["id"] for item in data1["items"]]
    ids2 = [item["id"] for item in data2["items"]]
    assert ids1 == ids2


@pytest.mark.asyncio
async def test_list_participants__invalid_page__returns_422(
    test_env, client: AsyncClient, auth_cookies: dict
):
    """Test invalid page parameter returns 422."""
    response = await client.get("/api/participants?page=0", cookies=auth_cookies)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_participants__invalid_size__returns_422(
    test_env, client: AsyncClient, auth_cookies: dict
):
    """Test invalid size parameter (>100) returns 422."""
    response = await client.get("/api/participants?size=101", cookies=auth_cookies)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_participants__no_auth__returns_401(test_env, client: AsyncClient):
    """Test listing participants without authentication returns 401."""
    response = await client.get("/api/participants")

    assert response.status_code == 401
