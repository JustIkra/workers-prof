"""
Comprehensive tests for metrics endpoints (S2-01).

Tests cover:
- MetricDef CRUD (POST/GET/PUT/DELETE /api/metric-defs)
- ExtractedMetric CRUD (GET/POST/PUT /api/reports/{id}/metrics)
- Uniqueness constraint (report_id, metric_def_id)
- Value range validation [min_value, max_value]
- Bulk create/update extracted metrics
- Authentication requirements
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FileRef, MetricDef, Participant, Report, User
from app.services.auth import create_user

# ===== Helper Fixtures =====


@pytest.fixture
async def active_user(db_session: AsyncSession) -> User:
    """Create an active user for authenticated requests."""
    user = await create_user(db_session, "metrics@example.com", "password123", role="USER")
    user.status = "ACTIVE"
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def auth_cookies(client: AsyncClient, active_user: User) -> dict:
    """Get authentication cookies for active user."""
    response = await client.post(
        "/api/auth/login", json={"email": "metrics@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    cookies = dict(response.cookies)
    client.cookies.clear()
    return cookies


@pytest.fixture
async def sample_metric_def(db_session: AsyncSession) -> MetricDef:
    """Create a sample metric definition for tests."""
    metric = MetricDef(
        code="METRIC_001",
        name="Тестовая метрика",
        name_ru="Тестовая метрика (RU)",
        description="Описание тестовой метрики",
        unit="баллы",
        min_value=Decimal("1.0"),
        max_value=Decimal("10.0"),
        active=True,
    )
    db_session.add(metric)
    await db_session.commit()
    await db_session.refresh(metric)
    return metric


@pytest.fixture
async def sample_report(db_session: AsyncSession) -> Report:
    """Create a sample report for extracted metrics tests."""
    # Create participant
    participant = Participant(
        full_name="Иван Иванов",
        birth_date=date(1990, 1, 15),
    )
    db_session.add(participant)
    await db_session.flush()

    # Create file_ref
    file_ref = FileRef(
        storage="LOCAL",
        bucket="local",
        key=f"reports/{participant.id}/test.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size_bytes=1024,
    )
    db_session.add(file_ref)
    await db_session.flush()

    # Create report
    report = Report(
        participant_id=participant.id,
        
        status="UPLOADED",
        file_ref_id=file_ref.id,
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)
    return report


# ===== MetricDef Tests =====


@pytest.mark.asyncio
async def test_create_metric_def__valid__returns_201(
    test_env, client: AsyncClient, auth_cookies: dict
):
    """Test successful metric definition creation."""
    response = await client.post(
        "/api/metric-defs",
        json={
            "code": "TEST_METRIC",
            "name": "Тестовая метрика",
            "name_ru": "Тестовая метрика (RU)",
            "description": "Описание",
            "unit": "баллы",
            "min_value": 1.0,
            "max_value": 10.0,
            "active": True,
        },
        cookies=auth_cookies,
    )

    assert response.status_code == 201
    data = response.json()

    assert data["code"] == "TEST_METRIC"
    assert data["name"] == "Тестовая метрика"
    assert data["name_ru"] == "Тестовая метрика (RU)"
    assert data["min_value"] == "1.00"
    assert data["max_value"] == "10.00"
    assert data["active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_create_metric_def__duplicate_code__returns_400(
    test_env, client: AsyncClient, auth_cookies: dict, sample_metric_def: MetricDef
):
    """Test that duplicate metric code returns 400."""
    response = await client.post(
        "/api/metric-defs",
        json={
            "code": sample_metric_def.code,
            "name": "Другая метрика",
            "min_value": 1.0,
            "max_value": 10.0,
        },
        cookies=auth_cookies,
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_metric_def__invalid_range__returns_400(
    test_env, client: AsyncClient, auth_cookies: dict
):
    """Test that min_value > max_value returns 400."""
    response = await client.post(
        "/api/metric-defs",
        json={
            "code": "INVALID_RANGE",
            "name": "Неверный диапазон",
            "min_value": 10.0,
            "max_value": 1.0,
        },
        cookies=auth_cookies,
    )

    assert response.status_code == 400
    assert "min_value" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_metric_defs__returns_all(
    test_env, client: AsyncClient, auth_cookies: dict, sample_metric_def: MetricDef
):
    """Test listing all metric definitions."""
    response = await client.get("/api/metric-defs", cookies=auth_cookies)

    assert response.status_code == 200
    data = response.json()

    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert any(item["code"] == sample_metric_def.code for item in data["items"])
    matching = next(item for item in data["items"] if item["code"] == sample_metric_def.code)
    assert matching["name_ru"] == "Тестовая метрика (RU)"


@pytest.mark.asyncio
async def test_list_metric_defs__active_only__filters_correctly(
    test_env, client: AsyncClient, auth_cookies: dict, db_session: AsyncSession
):
    """Test listing only active metric definitions."""
    # Create active and inactive metrics
    active = MetricDef(code="ACTIVE", name="Active", active=True)
    inactive = MetricDef(code="INACTIVE", name="Inactive", active=False)
    db_session.add_all([active, inactive])
    await db_session.commit()

    response = await client.get("/api/metric-defs?active_only=true", cookies=auth_cookies)

    assert response.status_code == 200
    data = response.json()

    codes = [item["code"] for item in data["items"]]
    assert "ACTIVE" in codes
    assert "INACTIVE" not in codes


@pytest.mark.asyncio
async def test_list_metric_defs__populates_missing_name_ru_from_localization(
    test_env,
    client: AsyncClient,
    auth_cookies: dict,
    db_session: AsyncSession,
):
    """Ensure list endpoint provides Russian name when DB field is empty."""
    existing = await db_session.execute(
        select(MetricDef).where(MetricDef.code == "abstractness")
    )
    metric = existing.scalar_one_or_none()
    if not metric:
        metric = MetricDef(
            code="abstractness",
            name="Abstractness",
            name_ru=None,
            description=None,
            unit="балл",
            min_value=Decimal("1"),
            max_value=Decimal("10"),
            active=True,
        )
        db_session.add(metric)
        await db_session.commit()
        await db_session.refresh(metric)
    else:
        metric.name_ru = None
        await db_session.commit()

    response = await client.get("/api/metric-defs", cookies=auth_cookies)

    assert response.status_code == 200
    data = response.json()
    entry = next(item for item in data["items"] if item["code"] == "abstractness")
    assert entry["name_ru"] == "Абстрактность"


@pytest.mark.asyncio
async def test_get_metric_def__exists__returns_200(
    test_env, client: AsyncClient, auth_cookies: dict, sample_metric_def: MetricDef
):
    """Test getting a metric definition by ID."""
    response = await client.get(
        f"/api/metric-defs/{sample_metric_def.id}",
        cookies=auth_cookies,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == str(sample_metric_def.id)
    assert data["code"] == sample_metric_def.code
    assert data["name_ru"] == "Тестовая метрика (RU)"


@pytest.mark.asyncio
async def test_get_metric_def__not_found__returns_404(
    test_env, client: AsyncClient, auth_cookies: dict
):
    """Test getting a non-existent metric definition returns 404."""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/metric-defs/{fake_id}", cookies=auth_cookies)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_metric_def__valid__returns_200(
    test_env, client: AsyncClient, auth_cookies: dict, sample_metric_def: MetricDef
):
    """Test updating a metric definition."""
    response = await client.put(
        f"/api/metric-defs/{sample_metric_def.id}",
        json={"name": "Обновленное имя", "name_ru": "Новое имя (RU)", "active": False},
        cookies=auth_cookies,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "Обновленное имя"
    assert data["name_ru"] == "Новое имя (RU)"
    assert data["active"] is False


@pytest.mark.asyncio
async def test_delete_metric_def__exists__returns_200(
    test_env, client: AsyncClient, auth_cookies: dict, sample_metric_def: MetricDef
):
    """Test deleting a metric definition."""
    response = await client.delete(
        f"/api/metric-defs/{sample_metric_def.id}",
        cookies=auth_cookies,
    )

    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]


# ===== ExtractedMetric Tests =====


@pytest.mark.asyncio
async def test_create_extracted_metric__valid__returns_201(
    test_env,
    client: AsyncClient,
    auth_cookies: dict,
    sample_report: Report,
    sample_metric_def: MetricDef,
):
    """Test creating an extracted metric."""
    response = await client.post(
        f"/api/reports/{sample_report.id}/metrics",
        json={
            "metric_def_id": str(sample_metric_def.id),
            "value": 7.5,
            "source": "MANUAL",
            "notes": "Тестовая заметка",
        },
        cookies=auth_cookies,
    )

    assert response.status_code == 201
    data = response.json()

    assert data["report_id"] == str(sample_report.id)
    assert data["metric_def_id"] == str(sample_metric_def.id)
    assert data["value"] == "7.50"
    assert data["source"] == "MANUAL"


@pytest.mark.asyncio
async def test_create_extracted_metric__duplicate__updates_existing(
    test_env,
    client: AsyncClient,
    auth_cookies: dict,
    sample_report: Report,
    sample_metric_def: MetricDef,
):
    """Test that creating duplicate (report_id, metric_def_id) updates existing value."""
    # Create first metric
    response1 = await client.post(
        f"/api/reports/{sample_report.id}/metrics",
        json={
            "metric_def_id": str(sample_metric_def.id),
            "value": 5.0,
            "source": "OCR",
        },
        cookies=auth_cookies,
    )
    assert response1.status_code == 201
    metric_id = response1.json()["id"]

    # Create second with same report_id and metric_def_id
    response2 = await client.post(
        f"/api/reports/{sample_report.id}/metrics",
        json={
            "metric_def_id": str(sample_metric_def.id),
            "value": 8.0,
            "source": "MANUAL",
        },
        cookies=auth_cookies,
    )
    assert response2.status_code == 201

    # Should have same ID (updated, not created new)
    assert response2.json()["id"] == metric_id
    assert response2.json()["value"] == "8.00"
    assert response2.json()["source"] == "MANUAL"


@pytest.mark.asyncio
async def test_create_extracted_metric__below_min__returns_400(
    test_env,
    client: AsyncClient,
    auth_cookies: dict,
    sample_report: Report,
    sample_metric_def: MetricDef,
):
    """Test that value below min_value returns 400."""
    response = await client.post(
        f"/api/reports/{sample_report.id}/metrics",
        json={
            "metric_def_id": str(sample_metric_def.id),
            "value": 0.5,  # Below min_value=1.0
        },
        cookies=auth_cookies,
    )

    assert response.status_code == 400
    assert "below minimum" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_extracted_metric__above_max__returns_400(
    test_env,
    client: AsyncClient,
    auth_cookies: dict,
    sample_report: Report,
    sample_metric_def: MetricDef,
):
    """Test that value above max_value returns 400."""
    response = await client.post(
        f"/api/reports/{sample_report.id}/metrics",
        json={
            "metric_def_id": str(sample_metric_def.id),
            "value": 11.0,  # Above max_value=10.0
        },
        cookies=auth_cookies,
    )

    assert response.status_code == 400
    assert "above maximum" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_extracted_metrics__returns_all(
    test_env,
    client: AsyncClient,
    auth_cookies: dict,
    sample_report: Report,
    sample_metric_def: MetricDef,
):
    """Test listing all extracted metrics for a report."""
    # Create extracted metric
    await client.post(
        f"/api/reports/{sample_report.id}/metrics",
        json={"metric_def_id": str(sample_metric_def.id), "value": 7.0},
        cookies=auth_cookies,
    )

    # List metrics
    response = await client.get(
        f"/api/reports/{sample_report.id}/metrics",
        cookies=auth_cookies,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    # Check that metric_def is included
    assert "metric_def" in data["items"][0]
    assert data["items"][0]["metric_def"]["code"] == sample_metric_def.code


@pytest.mark.asyncio
async def test_bulk_create_extracted_metrics__valid__returns_200(
    test_env,
    client: AsyncClient,
    auth_cookies: dict,
    sample_report: Report,
    db_session: AsyncSession,
):
    """Test bulk creating/updating extracted metrics."""
    # Create multiple metric defs
    metrics = [
        MetricDef(code=f"BULK_{i}", name=f"Метрика {i}", min_value=1, max_value=10)
        for i in range(3)
    ]
    db_session.add_all(metrics)
    await db_session.commit()

    # Bulk create
    response = await client.post(
        f"/api/reports/{sample_report.id}/metrics/bulk",
        json={
            "metrics": [
                {"metric_def_id": str(m.id), "value": float(i + 5)} for i, m in enumerate(metrics)
            ]
        },
        cookies=auth_cookies,
    )

    assert response.status_code == 200
    assert "3" in response.json()["message"]


@pytest.mark.asyncio
async def test_update_extracted_metric__valid__returns_200(
    test_env,
    client: AsyncClient,
    auth_cookies: dict,
    sample_report: Report,
    sample_metric_def: MetricDef,
):
    """Test updating an extracted metric."""
    # Create metric
    await client.post(
        f"/api/reports/{sample_report.id}/metrics",
        json={"metric_def_id": str(sample_metric_def.id), "value": 5.0},
        cookies=auth_cookies,
    )

    # Update metric
    response = await client.put(
        f"/api/reports/{sample_report.id}/metrics/{sample_metric_def.id}",
        json={"value": 9.0, "notes": "Обновлено"},
        cookies=auth_cookies,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["value"] == "9.00"
    assert data["notes"] == "Обновлено"


@pytest.mark.asyncio
async def test_extracted_metric__no_auth__returns_401(
    test_env, client: AsyncClient, sample_report: Report
):
    """Test that accessing metrics without auth returns 401."""
    response = await client.get(f"/api/reports/{sample_report.id}/metrics")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_metric_def__no_auth__returns_401(test_env, client: AsyncClient):
    """Test that accessing metric defs without auth returns 401."""
    response = await client.get("/api/metric-defs")

    assert response.status_code == 401
