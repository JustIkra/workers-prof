"""
Tests for scoring service and API (S2-02, S2-03, S2-06).

Verifies:
- Correct calculation of professional fitness scores (S2-02)
- Generation of strengths and development areas (S2-03)
- Scoring history retrieval for participants (S2-06)
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.db.models import Report
from app.repositories.metric import ExtractedMetricRepository, MetricDefRepository
from app.repositories.participant import ParticipantRepository
from app.repositories.prof_activity import ProfActivityRepository
from app.repositories.scoring_result import ScoringResultRepository
from app.services.scoring import ScoringService

# ===== Fixtures =====


@pytest.fixture
async def participant_with_metrics(db_session):
    """Create a participant with extracted metrics matching the Batura A.A. example."""
    # Create participant
    participant_repo = ParticipantRepository(db_session)
    participant = await participant_repo.create(
        full_name="Test Participant", birth_date=date(1985, 1, 1), external_id="TEST001"
    )

    # Create metrics (13 metrics from the example)
    metric_repo = MetricDefRepository(db_session)
    metrics_data = [
        ("communicability", "Коммуникабельность", Decimal("7.5")),
        ("teamwork", "Командность", Decimal("6.5")),
        ("low_conflict", "Конфликтность (низкая)", Decimal("9.5")),
        ("team_soul", "Роль «Душа команды» (Белбин)", Decimal("9.5")),
        ("organization", "Организованность", Decimal("6.5")),
        ("responsibility", "Ответственность", Decimal("6.5")),
        ("nonverbal_logic", "Невербальная логика", Decimal("9.5")),
        ("info_processing", "Обработка информации", Decimal("5.0")),
        ("complex_problem_solving", "Комплексное решение проблем", Decimal("6.5")),
        ("morality_normativity", "Моральность / Нормативность", Decimal("9.0")),
        ("stress_resistance", "Стрессоустойчивость", Decimal("2.5")),
        ("leadership", "Лидерство", Decimal("2.5")),
        ("vocabulary", "Лексика", Decimal("2.5")),
    ]

    metric_defs = {}
    for code, name, _ in metrics_data:
        # Try to get existing or create new
        metric = await metric_repo.get_by_code(code)
        if not metric:
            metric = await metric_repo.create(
                code=code,
                name=name,
                name_ru=name,
                unit="балл",
                min_value=Decimal("0"),
                max_value=Decimal("10"),
                active=True,
            )
        metric_defs[code] = metric

    # Create a dummy file_ref and report for the participant
    from app.db.models import FileRef

    file_ref = FileRef(
        id=uuid4(),
        storage="LOCAL",
        bucket="test",
        key="test/report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size_bytes=1024,
    )
    db_session.add(file_ref)
    await db_session.flush()

    report = Report(
        id=uuid4(),
        participant_id=participant.id,
        
        status="EXTRACTED",
        file_ref_id=file_ref.id,
    )
    db_session.add(report)
    await db_session.flush()

    # Create extracted metrics (legacy)
    extracted_metric_repo = ExtractedMetricRepository(db_session)
    for code, _name, value in metrics_data:
        metric_def = metric_defs[code]
        await extracted_metric_repo.create_or_update(
            report_id=report.id,
            metric_def_id=metric_def.id,
            value=value,
            source="MANUAL",
            confidence=Decimal("1.0"),
        )

    # Create participant metrics (S2-08)
    from app.repositories.participant_metric import ParticipantMetricRepository

    participant_metric_repo = ParticipantMetricRepository(db_session)
    for code, _name, value in metrics_data:
        await participant_metric_repo.upsert(
            participant_id=participant.id,
            metric_code=code,
            value=value,
            confidence=Decimal("1.0"),
            source_report_id=report.id,
        )

    await db_session.commit()
    await db_session.refresh(participant)

    return participant, metric_defs


@pytest.fixture
async def weight_table_with_batura_weights(db_session, participant_with_metrics):
    """Create a weight table with weights from the Batura A.A. example."""
    from app.db.models import WeightTable

    _, metric_defs = participant_with_metrics

    # Get prof activity
    prof_activity_repo = ProfActivityRepository(db_session)
    prof_activities = await prof_activity_repo.list_all()
    prof_activity = next((pa for pa in prof_activities if "совещ" in pa.name.lower()), None)

    if not prof_activity:
        pytest.skip(
            "Professional activity 'meeting_facilitation' not found. Run seed migrations first."
        )

    # Check if active weight table exists
    existing = await prof_activity_repo.get_active_weight_table(prof_activity.id)
    if existing:
        return prof_activity, existing

    # Create weight table directly (not via service) to stay in same session
    weights_data = [
        {"metric_code": "communicability", "weight": "0.18"},
        {"metric_code": "teamwork", "weight": "0.10"},
        {"metric_code": "low_conflict", "weight": "0.07"},
        {"metric_code": "team_soul", "weight": "0.08"},
        {"metric_code": "organization", "weight": "0.08"},
        {"metric_code": "responsibility", "weight": "0.07"},
        {"metric_code": "nonverbal_logic", "weight": "0.10"},
        {"metric_code": "info_processing", "weight": "0.05"},
        {"metric_code": "complex_problem_solving", "weight": "0.05"},
        {"metric_code": "morality_normativity", "weight": "0.10"},
        {"metric_code": "stress_resistance", "weight": "0.05"},
        {"metric_code": "leadership", "weight": "0.04"},
        {"metric_code": "vocabulary", "weight": "0.03"},
    ]

    weight_table = WeightTable(
        id=uuid4(),
        prof_activity_id=prof_activity.id,
        version=1,
        weights=weights_data,
        is_active=True,  # Directly set as active
        metadata_json={"source": "test_fixture"},
    )

    db_session.add(weight_table)
    await db_session.commit()
    await db_session.refresh(weight_table)

    return prof_activity, weight_table


# ===== Service Tests =====


@pytest.mark.asyncio
async def test_calculate_score__with_batura_data__returns_71_25_percent(
    db_session, participant_with_metrics, weight_table_with_batura_weights
):
    """
    Test scoring calculation with Batura A.A. reference data.

    Expected result: 71.25% based on test metrics and weights.
    Formula: score_pct = Σ(value × weight) × 10
    """
    participant, _ = participant_with_metrics
    prof_activity, weight_table = weight_table_with_batura_weights

    scoring_service = ScoringService(db_session)

    result = await scoring_service.calculate_score(
        participant_id=participant.id, prof_activity_code=prof_activity.code
    )

    # Verify score matches calculation
    assert result["score_pct"] == Decimal("71.25"), f"Expected 71.25, got {result['score_pct']}"
    assert result["weight_table_version"] == weight_table.version
    assert len(result["details"]) == 13  # 13 metrics
    assert result["missing_metrics"] == []
    assert "scoring_result_id" in result

    # Verify result was saved to database
    scoring_result_repo = ScoringResultRepository(db_session)
    saved_result = await scoring_result_repo.get_by_id(result["scoring_result_id"])
    assert saved_result is not None
    assert saved_result.participant_id == participant.id
    assert saved_result.weight_table_id == weight_table.id
    assert saved_result.score_pct == Decimal("71.25")


@pytest.mark.asyncio
async def test_calculate_score__missing_metrics__raises_error(
    db_session, weight_table_with_batura_weights
):
    """
    Test that missing metrics raise a ValueError.
    """
    prof_activity, _ = weight_table_with_batura_weights

    # Create participant without metrics
    participant_repo = ParticipantRepository(db_session)
    participant = await participant_repo.create(
        full_name="Empty Participant", birth_date=date(1990, 1, 1), external_id="EMPTY001"
    )

    scoring_service = ScoringService(db_session)

    with pytest.raises(ValueError, match="Missing extracted metrics"):
        await scoring_service.calculate_score(
            participant_id=participant.id, prof_activity_code=prof_activity.code
        )


@pytest.mark.asyncio
async def test_calculate_score__no_active_weight_table__raises_error(
    db_session, participant_with_metrics
):
    """
    Test that missing active weight table raises a ValueError.
    """
    participant, _ = participant_with_metrics

    # Use a prof activity code that doesn't exist
    scoring_service = ScoringService(db_session)

    with pytest.raises(ValueError, match="Professional activity .* not found"):
        await scoring_service.calculate_score(
            participant_id=participant.id, prof_activity_code="nonexistent_activity"
        )


# ===== API Tests =====


@pytest.mark.asyncio
async def test_api_calculate_score__with_valid_data__returns_200(
    client,
    db_session,
    participant_with_metrics,
    weight_table_with_batura_weights,
    active_user_token,
):
    """
    Test API endpoint for scoring calculation (S2-02, S2-03).
    """
    participant, _ = participant_with_metrics
    prof_activity, _ = weight_table_with_batura_weights

    response = await client.post(
        f"/api/scoring/participants/{participant.id}/calculate",
        params={"activity_code": prof_activity.code},
        cookies={"access_token": active_user_token},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["participant_id"] == str(participant.id)
    assert data["prof_activity_code"] == prof_activity.code
    assert Decimal(str(data["score_pct"])) == Decimal("71.25")
    assert len(data["details"]) == 13
    assert data["missing_metrics"] == []
    assert "scoring_result_id" in data

    # Verify strengths and dev_areas are present (S2-03)
    assert "strengths" in data
    assert "dev_areas" in data
    assert isinstance(data["strengths"], list)
    assert isinstance(data["dev_areas"], list)
    assert len(data["strengths"]) <= 5
    assert len(data["dev_areas"]) <= 5
    assert data["recommendations_status"] in {"pending", "ready", "error", "disabled"}
    assert "recommendations_error" in data

    # Check strengths structure
    if len(data["strengths"]) > 0:
        strength_item = data["strengths"][0]
        assert "metric_code" in strength_item
        assert "metric_name" in strength_item
        assert "value" in strength_item
        assert "weight" in strength_item

    # Verify result was saved to database
    scoring_result_repo = ScoringResultRepository(db_session)
    saved_result = await scoring_result_repo.get_by_id(data["scoring_result_id"])
    assert saved_result is not None
    assert saved_result.participant_id == participant.id
    assert saved_result.score_pct == Decimal("71.25")
    assert saved_result.strengths is not None
    assert saved_result.dev_areas is not None
    assert saved_result.recommendations_status in {"pending", "ready", "error", "disabled"}


@pytest.mark.asyncio
async def test_api_calculate_score__unauthorized__returns_401(
    client, participant_with_metrics, weight_table_with_batura_weights
):
    """
    Test that unauthorized requests are rejected.
    """
    participant, _ = participant_with_metrics
    prof_activity, _ = weight_table_with_batura_weights

    response = await client.post(
        f"/api/scoring/participants/{participant.id}/calculate",
        params={"activity_code": prof_activity.code},
    )

    assert response.status_code == 401


# ===== S2-03: Strengths/Dev Areas Tests =====


@pytest.mark.asyncio
async def test_strengths_dev_areas__with_batura_data__returns_correct_items(
    db_session, participant_with_metrics, weight_table_with_batura_weights
):
    """
    Test that strengths and dev_areas are correctly generated (S2-03).

    Expected strengths (top 5 highest values):
    1. Конфликтность (низкая): 9.5
    2. Роль «Душа команды»: 9.5
    3. Невербальная логика: 9.5
    4. Моральность / Нормативность: 9.0
    5. Коммуникабельность: 7.5

    Expected dev_areas (top 5 lowest values):
    1. Лидерство: 2.5
    2. Лексика: 2.5
    3. Стрессоустойчивость: 2.5
    4. Обработка информации: 5.0
    5. Командность: 6.5
    """
    participant, _ = participant_with_metrics
    prof_activity, _ = weight_table_with_batura_weights

    scoring_service = ScoringService(db_session)
    result = await scoring_service.calculate_score(
        participant_id=participant.id, prof_activity_code=prof_activity.code
    )

    # Verify strengths structure
    assert "strengths" in result
    assert isinstance(result["strengths"], list)
    assert len(result["strengths"]) <= 5, "Strengths should have at most 5 items"

    # Verify dev_areas structure
    assert "dev_areas" in result
    assert isinstance(result["dev_areas"], list)
    assert len(result["dev_areas"]) <= 5, "Dev areas should have at most 5 items"

    # Check strengths are high-value metrics
    strengths = result["strengths"]
    assert len(strengths) == 5

    # First strength should be one of the metrics with value 9.5
    first_value = Decimal(strengths[0]["value"])
    assert first_value == Decimal("9.5")

    # Check that all strengths have required fields
    for item in strengths:
        assert "metric_code" in item
        assert "metric_name" in item
        assert "value" in item
        assert "weight" in item
        assert Decimal(item["value"]) >= Decimal("1.0")
        assert Decimal(item["value"]) <= Decimal("10.0")

    # Check dev_areas are low-value metrics
    dev_areas = result["dev_areas"]
    assert len(dev_areas) == 5

    # First dev_area should have value 2.5 (lowest)
    first_dev_value = Decimal(dev_areas[0]["value"])
    assert first_dev_value == Decimal("2.5")

    # Check that all dev_areas have required fields
    for item in dev_areas:
        assert "metric_code" in item
        assert "metric_name" in item
        assert "value" in item
        assert "weight" in item

    # Verify saved to database with strengths/dev_areas
    scoring_result_repo = ScoringResultRepository(db_session)
    saved_result = await scoring_result_repo.get_by_id(result["scoring_result_id"])
    assert saved_result.strengths is not None
    assert saved_result.dev_areas is not None
    assert len(saved_result.strengths) == 5
    assert len(saved_result.dev_areas) == 5


@pytest.mark.asyncio
async def test_strengths_dev_areas__stable_sorting__same_values_sorted_by_code(
    db_session, participant_with_metrics, weight_table_with_batura_weights
):
    """
    Test that metrics with same values are sorted by code for stability (S2-03 AC).

    Multiple metrics have value 2.5 (leadership, vocabulary, stress_resistance).
    They should appear in alphabetical order by metric_code.
    """
    participant, _ = participant_with_metrics
    prof_activity, _ = weight_table_with_batura_weights

    scoring_service = ScoringService(db_session)
    result = await scoring_service.calculate_score(
        participant_id=participant.id, prof_activity_code=prof_activity.code
    )

    dev_areas = result["dev_areas"]

    # Find all metrics with value 2.5
    metrics_with_2_5 = [item for item in dev_areas if Decimal(item["value"]) == Decimal("2.5")]

    # Should have 3 metrics with value 2.5
    assert len(metrics_with_2_5) >= 3

    # Check they are sorted alphabetically by metric_code
    codes_with_2_5 = [item["metric_code"] for item in metrics_with_2_5]
    assert codes_with_2_5 == sorted(
        codes_with_2_5
    ), f"Metrics with same value should be sorted by code. Got: {codes_with_2_5}"


@pytest.mark.asyncio
async def test_strengths_dev_areas__no_duplicates__each_metric_once(
    db_session, participant_with_metrics, weight_table_with_batura_weights
):
    """
    Test that no metric appears more than once in strengths or dev_areas (S2-03 AC).
    """
    participant, _ = participant_with_metrics
    prof_activity, _ = weight_table_with_batura_weights

    scoring_service = ScoringService(db_session)
    result = await scoring_service.calculate_score(
        participant_id=participant.id, prof_activity_code=prof_activity.code
    )

    # Check no duplicates in strengths
    strengths_codes = [item["metric_code"] for item in result["strengths"]]
    assert len(strengths_codes) == len(set(strengths_codes)), "Strengths should not have duplicates"

    # Check no duplicates in dev_areas
    dev_areas_codes = [item["metric_code"] for item in result["dev_areas"]]
    assert len(dev_areas_codes) == len(set(dev_areas_codes)), "Dev areas should not have duplicates"


@pytest.mark.asyncio
async def test_strengths_dev_areas__reproducibility__same_input_same_output(
    db_session, participant_with_metrics, weight_table_with_batura_weights
):
    """
    Test that repeated calculations produce identical results (S2-03 AC: reproducibility).
    """
    participant, _ = participant_with_metrics
    prof_activity, _ = weight_table_with_batura_weights

    scoring_service = ScoringService(db_session)

    # First calculation
    result1 = await scoring_service.calculate_score(
        participant_id=participant.id, prof_activity_code=prof_activity.code
    )

    # Second calculation (should create new scoring_result but with same strengths/dev_areas)
    result2 = await scoring_service.calculate_score(
        participant_id=participant.id, prof_activity_code=prof_activity.code
    )

    # Verify results are identical (except scoring_result_id which is new)
    assert result1["strengths"] == result2["strengths"], "Strengths should be reproducible"
    assert result1["dev_areas"] == result2["dev_areas"], "Dev areas should be reproducible"
    assert result1["score_pct"] == result2["score_pct"]

    # But scoring_result_id should be different (new record)
    assert result1["scoring_result_id"] != result2["scoring_result_id"]


@pytest.mark.asyncio
async def test_strengths_dev_areas__max_five_elements__enforced(
    db_session, participant_with_metrics, weight_table_with_batura_weights
):
    """
    Test that strengths and dev_areas are limited to maximum 5 elements (S2-03 AC).
    """
    participant, _ = participant_with_metrics
    prof_activity, _ = weight_table_with_batura_weights

    scoring_service = ScoringService(db_session)
    result = await scoring_service.calculate_score(
        participant_id=participant.id, prof_activity_code=prof_activity.code
    )

    # Explicit check for ≤5 constraint
    assert (
        len(result["strengths"]) <= 5
    ), f"Strengths must have ≤5 elements, got {len(result['strengths'])}"
    assert (
        len(result["dev_areas"]) <= 5
    ), f"Dev areas must have ≤5 elements, got {len(result['dev_areas'])}"


# ===== BUG-02: Decimal Quantize Tests =====


@pytest.mark.asyncio
async def test_calculate_score__with_fractional_decimal_values__no_quantize_error(
    db_session, weight_table_with_batura_weights
):
    """
    Test that fractional Decimal values (e.g., 7.5, 0.075) don't cause quantize errors (BUG-02).

    This test verifies that the scoring calculation handles Decimal multiplication
    and quantization correctly when dealing with fractional values that have
    more precision than the target format (0.01).

    Regression test for: Decimal quantize requires exponent error
    """
    from app.repositories.participant_metric import ParticipantMetricRepository

    # Create participant with fractional metric values
    participant_repo = ParticipantRepository(db_session)
    participant = await participant_repo.create(
        full_name="Fractional Test Participant",
        birth_date=date(1990, 1, 1),
        external_id="FRAC001",
    )

    # Create a dummy report
    from app.db.models import FileRef, Report

    file_ref = FileRef(
        id=uuid4(),
        storage="LOCAL",
        bucket="test",
        key="test/report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size_bytes=1024,
    )
    db_session.add(file_ref)
    await db_session.flush()

    report = Report(
        id=uuid4(),
        participant_id=participant.id,
        status="EXTRACTED",
        file_ref_id=file_ref.id,
    )
    db_session.add(report)
    await db_session.flush()

    # Add participant metrics with fractional values (like those from Gemini extraction)
    participant_metric_repo = ParticipantMetricRepository(db_session)

    fractional_metrics = [
        ("communicability", Decimal("7.5")),
        ("teamwork", Decimal("6.3")),
        ("low_conflict", Decimal("9.7")),
        ("team_soul", Decimal("9.1")),
        ("organization", Decimal("6.8")),
        ("responsibility", Decimal("6.4")),
        ("nonverbal_logic", Decimal("9.2")),
        ("info_processing", Decimal("5.5")),
        ("complex_problem_solving", Decimal("6.7")),
        ("morality_normativity", Decimal("8.9")),
        ("stress_resistance", Decimal("2.3")),
        ("leadership", Decimal("2.1")),
        ("vocabulary", Decimal("2.6")),
    ]

    for code, value in fractional_metrics:
        await participant_metric_repo.upsert(
            participant_id=participant.id,
            metric_code=code,
            value=value,
            confidence=Decimal("0.85"),  # Also fractional confidence
            source_report_id=report.id,
        )

    await db_session.commit()

    prof_activity, _ = weight_table_with_batura_weights

    # This should NOT raise "Decimal quantize requires exponent" error
    scoring_service = ScoringService(db_session)

    result = await scoring_service.calculate_score(
        participant_id=participant.id, prof_activity_code=prof_activity.code
    )

    # Verify calculation completed successfully
    assert "score_pct" in result
    assert isinstance(result["score_pct"], Decimal)
    assert result["score_pct"] > Decimal("0")
    assert result["score_pct"] <= Decimal("100")

    # Verify all details have properly quantized contributions
    assert len(result["details"]) == 13
    for detail in result["details"]:
        assert "contribution" in detail
        contribution = Decimal(detail["contribution"])
        # Verify contribution is quantized to 0.01
        assert contribution == contribution.quantize(Decimal("0.01"))


@pytest.mark.asyncio
async def test_generate_final_report__with_fractional_values__no_quantize_error(
    db_session, weight_table_with_batura_weights
):
    """
    Test that generate_final_report handles fractional Decimal values correctly (BUG-02).

    This specifically tests the generate_final_report method which had the missing
    rounding parameter on line 343 of scoring.py.
    """
    from app.repositories.participant_metric import ParticipantMetricRepository

    # Create participant
    participant_repo = ParticipantRepository(db_session)
    participant = await participant_repo.create(
        full_name="Final Report Test",
        birth_date=date(1990, 1, 1),
        external_id="FR001",
    )

    # Create report
    from app.db.models import FileRef, Report

    file_ref = FileRef(
        id=uuid4(),
        storage="LOCAL",
        bucket="test",
        key="test/report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size_bytes=1024,
    )
    db_session.add(file_ref)
    await db_session.flush()

    report = Report(
        id=uuid4(),
        participant_id=participant.id,
        status="EXTRACTED",
        file_ref_id=file_ref.id,
    )
    db_session.add(report)
    await db_session.flush()

    # Add metrics with fractional values
    participant_metric_repo = ParticipantMetricRepository(db_session)
    metrics = [
        ("communicability", Decimal("7.5")),
        ("teamwork", Decimal("6.5")),
        ("low_conflict", Decimal("9.5")),
        ("team_soul", Decimal("9.5")),
        ("organization", Decimal("6.5")),
        ("responsibility", Decimal("6.5")),
        ("nonverbal_logic", Decimal("9.5")),
        ("info_processing", Decimal("5.0")),
        ("complex_problem_solving", Decimal("6.5")),
        ("morality_normativity", Decimal("9.0")),
        ("stress_resistance", Decimal("2.5")),
        ("leadership", Decimal("2.5")),
        ("vocabulary", Decimal("2.5")),
    ]

    for code, value in metrics:
        await participant_metric_repo.upsert(
            participant_id=participant.id,
            metric_code=code,
            value=value,
            confidence=Decimal("0.85"),
            source_report_id=report.id,
        )

    await db_session.commit()

    prof_activity, _ = weight_table_with_batura_weights

    # First calculate score to create scoring_result
    scoring_service = ScoringService(db_session)
    await scoring_service.calculate_score(
        participant_id=participant.id, prof_activity_code=prof_activity.code
    )

    # Now generate final report - this should NOT raise quantize error
    final_report = await scoring_service.generate_final_report(
        participant_id=participant.id, prof_activity_code=prof_activity.code
    )

    # Verify final report was generated successfully
    assert "score_pct" in final_report
    assert "metrics" in final_report
    assert len(final_report["metrics"]) == 13

    # Verify all metric contributions are properly quantized
    for metric in final_report["metrics"]:
        assert "contribution" in metric
        contribution = metric["contribution"]
        # Verify it's a Decimal quantized to 0.01
        assert contribution == contribution.quantize(Decimal("0.01"))


# ===== S2-06: Scoring History Tests =====


@pytest.mark.asyncio
async def test_api_get_scoring_history__with_multiple_results__returns_200_sorted_desc(
    client,
    db_session,
    participant_with_metrics,
    weight_table_with_batura_weights,
    active_user_token,
):
    """
    Test API endpoint for scoring history retrieval (S2-06).

    Verifies:
    - Returns 200 with list of scoring results
    - Results are sorted by created_at DESC
    - Contains all required fields
    """
    participant, _ = participant_with_metrics
    prof_activity, _ = weight_table_with_batura_weights

    # Create multiple scoring results
    scoring_service = ScoringService(db_session)

    # First calculation
    result1 = await scoring_service.calculate_score(
        participant_id=participant.id, prof_activity_code=prof_activity.code
    )

    # Second calculation
    result2 = await scoring_service.calculate_score(
        participant_id=participant.id, prof_activity_code=prof_activity.code
    )

    # Get scoring history
    response = await client.get(
        f"/api/scoring/participants/{participant.id}/scores",
        cookies={"access_token": active_user_token},
    )

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 2

    # Verify sorting: most recent first
    first_item = data["items"][0]
    second_item = data["items"][1]

    # Most recent result should be first (result2)
    assert first_item["id"] == str(result2["scoring_result_id"])
    assert second_item["id"] == str(result1["scoring_result_id"])

    # Verify structure of first item
    assert first_item["participant_id"] == str(participant.id)
    assert first_item["prof_activity_code"] == prof_activity.code
    assert first_item["prof_activity_name"] == prof_activity.name
    assert Decimal(str(first_item["score_pct"])) == Decimal("71.25")
    assert "strengths" in first_item
    assert "dev_areas" in first_item
    assert "recommendations" in first_item
    assert "created_at" in first_item

    # Verify ISO 8601 datetime format
    assert "T" in first_item["created_at"]


@pytest.mark.asyncio
async def test_api_get_scoring_history__with_limit__respects_limit(
    client,
    db_session,
    participant_with_metrics,
    weight_table_with_batura_weights,
    active_user_token,
):
    """
    Test that limit parameter is respected (S2-06).
    """
    participant, _ = participant_with_metrics
    prof_activity, _ = weight_table_with_batura_weights

    # Create 5 scoring results
    scoring_service = ScoringService(db_session)
    for _ in range(5):
        await scoring_service.calculate_score(
            participant_id=participant.id, prof_activity_code=prof_activity.code
        )

    # Get history with limit=3
    response = await client.get(
        f"/api/scoring/participants/{participant.id}/scores",
        params={"limit": 3},
        cookies={"access_token": active_user_token},
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_api_get_scoring_history__no_results__returns_empty_list(
    client, db_session, participant_with_metrics, active_user_token
):
    """
    Test that empty list is returned when participant has no scoring results (S2-06).
    """
    participant, _ = participant_with_metrics

    response = await client.get(
        f"/api/scoring/participants/{participant.id}/scores",
        cookies={"access_token": active_user_token},
    )

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert data["items"] == []


@pytest.mark.asyncio
async def test_api_get_scoring_history__participant_not_found__returns_404(
    client, active_user_token
):
    """
    Test that 404 is returned for non-existent participant (S2-06).
    """
    non_existent_id = uuid4()

    response = await client.get(
        f"/api/scoring/participants/{non_existent_id}/scores",
        cookies={"access_token": active_user_token},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_get_scoring_history__unauthorized__returns_401(client, participant_with_metrics):
    """
    Test that unauthorized requests are rejected (S2-06).
    """
    participant, _ = participant_with_metrics

    response = await client.get(f"/api/scoring/participants/{participant.id}/scores")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_get_scoring_history__with_recommendations__returns_structured_items(
    client, db_session, participant_with_metrics, active_user_token
):
    """
    Test that recommendations are returned as full objects in scoring history (AI-09 fix).
    """
    participant, _ = participant_with_metrics

    # Create a scoring result with recommendations
    scoring_repo = ScoringResultRepository(db_session)
    prof_activity_repo = ProfActivityRepository(db_session)

    # Get developer activity and its weight table
    prof_activity = await prof_activity_repo.get_by_code("developer")
    weight_table = await prof_activity_repo.get_active_weight_table(prof_activity.id)

    # Create scoring result with recommendations in dict format
    recommendations_data = [
        {"title": "Курс по стрессоустойчивости", "link_url": "https://example.com/stress", "priority": 1},
        {"title": "Тренинг по лидерству", "link_url": "https://example.com/leadership", "priority": 2},
        {"title": "Курс по расширению словарного запаса", "link_url": "", "priority": 3},
    ]

    scoring_result = await scoring_repo.create(
        participant_id=participant.id,
        weight_table_id=weight_table.id,
        score_pct=Decimal("65.50"),
        strengths=[],
        dev_areas=[],
        recommendations=recommendations_data,
        compute_notes="Test scoring with recommendations",
        recommendations_status="ready",
    )

    # Get scoring history via API
    response = await client.get(
        f"/api/participants/{participant.id}/scores",
        cookies={"access_token": active_user_token},
    )

    assert response.status_code == 200
    data = response.json()

    assert "results" in data
    assert len(data["results"]) == 1

    history_item = data["results"][0]
    assert "recommendations" in history_item
    assert history_item["recommendations"] is not None
    assert len(history_item["recommendations"]) == 3

    # Verify recommendations are returned as dicts with expected keys
    first_rec = history_item["recommendations"][0]
    assert set(first_rec.keys()) == {"title", "link_url", "priority"}
    assert first_rec["title"] == "Курс по стрессоустойчивости"
    assert history_item["recommendations_status"] == "ready"
    assert history_item["recommendations_error"] is None
