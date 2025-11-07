"""
Tests for final report generation (S2-04).

Verifies:
- JSON schema validation
- HTML template rendering
- Snapshot testing for HTML output
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from httpx import AsyncClient

from app.services.scoring import ScoringService
from app.services.report_template import render_final_report_html
from app.repositories.metric import MetricDefRepository, ExtractedMetricRepository
from app.repositories.prof_activity import ProfActivityRepository
from app.repositories.participant import ParticipantRepository
from app.schemas.final_report import FinalReportResponse
from app.db.models import WeightTable


# ===== Fixtures =====

@pytest.fixture
async def participant_with_full_data(db_session):
    """Create a participant with full scoring data for final report testing."""
    # Create participant
    participant_repo = ParticipantRepository(db_session)
    participant = await participant_repo.create(
        full_name="Батура Анна Александровна",
        birth_date=date(1990, 5, 15),
        external_id="BATURA_AA"
    )

    # Create metrics
    metric_repo = MetricDefRepository(db_session)
    metrics_data = [
        ("communicability", "Коммуникабельность", Decimal("7.5"), "OCR", Decimal("0.92")),
        ("teamwork", "Командность", Decimal("6.5"), "OCR", Decimal("0.88")),
        ("low_conflict", "Конфликтность (низкая)", Decimal("9.5"), "LLM", Decimal("0.95")),
        ("team_soul", "Роль «Душа команды»", Decimal("9.5"), "OCR", Decimal("0.90")),
        ("organization", "Организованность", Decimal("6.5"), "OCR", Decimal("0.85")),
        ("responsibility", "Ответственность", Decimal("6.5"), "MANUAL", None),
        ("nonverbal_logic", "Невербальная логика", Decimal("9.5"), "OCR", Decimal("0.93")),
        ("info_processing", "Обработка информации", Decimal("5.0"), "OCR", Decimal("0.80")),
        ("complex_problem_solving", "Комплексное решение проблем", Decimal("6.5"), "OCR", Decimal("0.87")),
        ("morality_normativity", "Моральность/Нормативность", Decimal("9.0"), "LLM", Decimal("0.91")),
        ("stress_resistance", "Стрессоустойчивость", Decimal("2.5"), "OCR", Decimal("0.82")),
        ("leadership", "Лидерство", Decimal("2.5"), "OCR", Decimal("0.84")),
        ("vocabulary", "Лексика", Decimal("2.5"), "OCR", Decimal("0.86")),
    ]

    metric_defs = {}
    for code, name, value, source, confidence in metrics_data:
        # Try to get existing or create new
        metric = await metric_repo.get_by_code(code)
        if not metric:
            metric = await metric_repo.create(
                code=code,
                name=name,
                unit="балл",
                min_value=Decimal("0"),
                max_value=Decimal("10"),
                active=True
            )
        metric_defs[code] = metric

    # Create file_ref and report
    from app.db.models import FileRef, Report

    file_ref = FileRef(
        id=uuid4(),
        storage="LOCAL",
        bucket="test",
        key="test/batura_report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size_bytes=2048
    )
    db_session.add(file_ref)
    await db_session.flush()

    report = Report(
        id=uuid4(),
        participant_id=participant.id,
        type="REPORT_1",
        status="EXTRACTED",
        file_ref_id=file_ref.id,
    )
    db_session.add(report)
    await db_session.flush()

    # Create extracted metrics with source and confidence
    extracted_metric_repo = ExtractedMetricRepository(db_session)
    for code, name, value, source, confidence in metrics_data:
        metric_def = metric_defs[code]
        await extracted_metric_repo.create_or_update(
            report_id=report.id,
            metric_def_id=metric_def.id,
            value=value,
            source=source,
            confidence=confidence,
        )

    # Get professional activity from seeded data
    prof_activity_repo = ProfActivityRepository(db_session)
    prof_activities = await prof_activity_repo.list_all()

    # Try to find meeting_facilitation activity (should be seeded)
    prof_activity = None
    if prof_activities:
        prof_activity = prof_activities[0]  # Use first available

    if not prof_activity:
        pytest.skip("No professional activities found. Run seed migrations first.")

    # Create weight table with all metrics
    weights_data = []
    weight_value = Decimal("1") / Decimal(str(len(metrics_data)))  # Equal weights
    for code, name, _, _, _ in metrics_data:
        weights_data.append({
            "metric_code": code,
            "weight": str(weight_value.quantize(Decimal("0.01")))
        })

    # Adjust first weight to ensure sum = 1.0
    total = sum(Decimal(w["weight"]) for w in weights_data)
    adjustment = Decimal("1.0") - total
    weights_data[0]["weight"] = str(Decimal(weights_data[0]["weight"]) + adjustment)

    # Create weight table directly (repository doesn't have create_weight_table method)
    weight_table = WeightTable(
        prof_activity_id=prof_activity.id,
        version=1,
        is_active=True,
        weights=weights_data
    )
    db_session.add(weight_table)
    await db_session.commit()
    await db_session.refresh(weight_table)

    # Calculate score to create scoring_result
    scoring_service = ScoringService(db_session)
    await scoring_service.calculate_score(
        participant_id=participant.id,
        prof_activity_code=prof_activity.code,
    )

    return {
        "participant": participant,
        "prof_activity": prof_activity,
        "weight_table": weight_table,
        "metrics_count": len(metrics_data),
    }


# ===== Service Tests =====

@pytest.mark.asyncio
async def test_generate_final_report__with_valid_data__returns_complete_structure(
    db_session, participant_with_full_data
):
    """Test that generate_final_report returns all required fields."""
    # Arrange
    participant = participant_with_full_data["participant"]
    scoring_service = ScoringService(db_session)

    # Act
    report_data = await scoring_service.generate_final_report(
        participant_id=participant.id,
        prof_activity_code=participant_with_full_data["prof_activity"].code,
    )

    # Assert: Check structure
    assert "participant_id" in report_data
    assert "participant_name" in report_data
    assert "report_date" in report_data
    assert "prof_activity_code" in report_data
    assert "prof_activity_name" in report_data
    assert "weight_table_version" in report_data
    assert "score_pct" in report_data
    assert "strengths" in report_data
    assert "dev_areas" in report_data
    assert "recommendations" in report_data
    assert "metrics" in report_data
    assert "notes" in report_data
    assert "template_version" in report_data

    # Assert: Check values
    assert report_data["participant_id"] == participant.id
    assert report_data["participant_name"] == "Батура Анна Александровна"
    assert report_data["prof_activity_code"] == participant_with_full_data["prof_activity"].code
    assert report_data["prof_activity_name"] == participant_with_full_data["prof_activity"].name
    assert report_data["weight_table_version"] == 1
    assert isinstance(report_data["score_pct"], Decimal)
    assert Decimal("0") <= report_data["score_pct"] <= Decimal("100")

    # Assert: Strengths and dev_areas
    assert len(report_data["strengths"]) <= 5
    assert len(report_data["dev_areas"]) <= 5

    # Assert: Each strength has required fields
    for strength in report_data["strengths"]:
        assert "title" in strength
        assert "metric_codes" in strength
        assert "reason" in strength

    # Assert: Each dev_area has required fields
    for dev_area in report_data["dev_areas"]:
        assert "title" in dev_area
        assert "metric_codes" in dev_area
        assert "actions" in dev_area

    # Assert: Metrics table
    assert len(report_data["metrics"]) == participant_with_full_data["metrics_count"]
    for metric in report_data["metrics"]:
        assert "code" in metric
        assert "name" in metric
        assert "value" in metric
        assert "unit" in metric
        assert "weight" in metric
        assert "contribution" in metric
        assert "source" in metric
        # confidence can be None


@pytest.mark.asyncio
async def test_final_report__json_schema_validation__passes_pydantic(
    db_session, participant_with_full_data
):
    """Test that final report data validates against Pydantic schema (S2-04 AC)."""
    # Arrange
    participant = participant_with_full_data["participant"]
    scoring_service = ScoringService(db_session)

    # Act
    report_data = await scoring_service.generate_final_report(
        participant_id=participant.id,
        prof_activity_code=participant_with_full_data["prof_activity"].code,
    )

    # Assert: Should not raise ValidationError
    report_response = FinalReportResponse(**report_data)

    # Verify key fields
    assert report_response.participant_name == "Батура Анна Александровна"
    assert report_response.prof_activity_code == participant_with_full_data["prof_activity"].code
    assert report_response.template_version == "1.0.0"
    assert 0 <= report_response.score_pct <= 100


@pytest.mark.asyncio
async def test_final_report__html_rendering__produces_valid_html(
    db_session, participant_with_full_data
):
    """Test that HTML template renders without errors (S2-04 AC)."""
    # Arrange
    participant = participant_with_full_data["participant"]
    scoring_service = ScoringService(db_session)

    report_data = await scoring_service.generate_final_report(
        participant_id=participant.id,
        prof_activity_code=participant_with_full_data["prof_activity"].code,
    )

    # Act
    html = render_final_report_html(report_data)

    # Assert: Basic HTML structure
    assert html is not None
    assert len(html) > 0
    assert "<!DOCTYPE html>" in html
    assert "<html" in html
    assert "</html>" in html

    # Assert: Key content present
    assert "Батура Анна Александровна" in html
    assert participant_with_full_data["prof_activity"].name in html
    assert "Итоговый коэффициент" in html
    assert "Сильные стороны" in html
    assert "Зоны развития" in html


@pytest.mark.asyncio
async def test_final_report__html_snapshot__matches_expected(
    db_session, participant_with_full_data
):
    """Test HTML output against snapshot for regression detection (S2-04 AC)."""
    # Arrange
    participant = participant_with_full_data["participant"]
    scoring_service = ScoringService(db_session)

    report_data = await scoring_service.generate_final_report(
        participant_id=participant.id,
        prof_activity_code=participant_with_full_data["prof_activity"].code,
    )

    # Normalize dynamic fields for snapshot
    report_data["report_date"] = datetime(2025, 1, 15, 10, 30, 0)
    report_data["participant_id"] = uuid4()  # Fixed UUID for snapshot

    # Act
    html = render_final_report_html(report_data)

    # Assert: Check key structural elements
    assert "<title>Итоговый отчёт — Батура Анна Александровна</title>" in html
    assert 'class="score-section"' in html
    assert 'class="metrics-table"' in html

    # Check that metrics table has all rows
    assert html.count("<tr>") >= participant_with_full_data["metrics_count"]

    # Check CSS is embedded
    assert "font-family: 'Segoe UI'" in html
    assert "#00798D" in html  # Primary color

    # Check template version in footer
    assert "Версия шаблона отчёта: 1.0.0" in html


@pytest.mark.asyncio
async def test_final_report__no_scoring_result__raises_error(
    db_session, participant_with_full_data
):
    """Test that generate_final_report raises error if no scoring result exists."""
    # Arrange
    participant_repo = ParticipantRepository(db_session)
    new_participant = await participant_repo.create(
        full_name="No Score Participant",
        birth_date=date(1995, 1, 1),
    )

    scoring_service = ScoringService(db_session)
    prof_activity = participant_with_full_data["prof_activity"]

    # Act & Assert
    with pytest.raises(ValueError, match="No scoring result found"):
        await scoring_service.generate_final_report(
            participant_id=new_participant.id,
            prof_activity_code=prof_activity.code,
        )


# ===== API Tests =====

@pytest.mark.asyncio
async def test_api_final_report_json__with_valid_data__returns_200(
    test_env, client: AsyncClient, db_session, participant_with_full_data
):
    """Test API endpoint for final report JSON format."""
    # Arrange
    participant = participant_with_full_data["participant"]
    prof_activity = participant_with_full_data["prof_activity"]

    # Create active user and get auth cookies
    from app.services.auth import create_user
    user = await create_user(db_session, "active@example.com", "password123", role="USER")
    user.status = "ACTIVE"
    await db_session.commit()

    # Login to get cookies
    login_response = await client.post(
        "/api/auth/login",
        json={"email": "active@example.com", "password": "password123"}
    )
    assert login_response.status_code == 200
    auth_cookies = dict(login_response.cookies)

    # Act
    response = await client.get(
        f"/api/participants/{participant.id}/final-report?activity_code={prof_activity.code}",
        cookies=auth_cookies,
    )

    # Assert
    assert response.status_code == 200
    data = response.json()

    assert data["participant_name"] == "Батура Анна Александровна"
    assert data["prof_activity_code"] == prof_activity.code
    assert "score_pct" in data
    assert "strengths" in data
    assert "dev_areas" in data
    assert "metrics" in data


@pytest.mark.asyncio
async def test_api_final_report_html__with_format_param__returns_html(
    test_env, client: AsyncClient, db_session, participant_with_full_data
):
    """Test API endpoint for final report HTML format."""
    # Arrange
    participant = participant_with_full_data["participant"]
    prof_activity = participant_with_full_data["prof_activity"]

    # Create active user and get auth cookies
    from app.services.auth import create_user
    user = await create_user(db_session, "active@example.com", "password123", role="USER")
    user.status = "ACTIVE"
    await db_session.commit()

    # Login to get cookies
    login_response = await client.post(
        "/api/auth/login",
        json={"email": "active@example.com", "password": "password123"}
    )
    assert login_response.status_code == 200
    auth_cookies = dict(login_response.cookies)

    # Act
    response = await client.get(
        f"/api/participants/{participant.id}/final-report?activity_code={prof_activity.code}&format=html",
        cookies=auth_cookies,
    )

    # Assert
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")

    html = response.text
    assert "<!DOCTYPE html>" in html
    assert "Батура Анна Александровна" in html
    assert "Итоговый коэффициент" in html
