"""
Regression test for BUG-02: 500 error when calculating scoring after version field removal.

After migration d952812cd1d6_remove_version_and_is_active_from_weight_table,
the scoring calculation failed because code was trying to access weight_table.version.

This test verifies that:
1. Scoring calculation completes successfully without version field
2. Response contains weight_table_id instead of weight_table_version
3. Final report generation works without version field
"""

import pytest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.db.models import (
    Participant,
    ProfActivity,
    WeightTable,
    ParticipantMetric,
)
from app.services.scoring import ScoringService


@pytest.mark.asyncio
@pytest.mark.integration
async def test_scoring_calculation_without_version_field(db_session):
    """
    Test that scoring calculation works after version field removal (BUG-02).

    AC:
    - POST /api/scoring/participants/{id}/calculate returns 200
    - Response contains weight_table_id (not weight_table_version)
    - No AttributeError when accessing weight_table fields
    """
    # Arrange: Create participant with metrics
    prof_activity = ProfActivity(
        id=uuid4(),
        code="developer",
        name="Software Developer",
        description="Test activity",
    )
    db_session.add(prof_activity)

    # Create weight table WITHOUT version or is_active fields
    weight_table = WeightTable(
        id=uuid4(),
        prof_activity_id=prof_activity.id,
        weights=[
            {"metric_code": "CODE_QUALITY", "metric_name": "Code Quality", "weight": "0.40"},
            {"metric_code": "TEAMWORK", "metric_name": "Teamwork", "weight": "0.30"},
            {"metric_code": "DELIVERY_SPEED", "metric_name": "Delivery Speed", "weight": "0.30"},
        ],
    )
    db_session.add(weight_table)

    participant = Participant(
        id=uuid4(),
        full_name="Test Developer",
        birth_date=date(1990, 1, 1),
    )
    db_session.add(participant)

    # Add participant metrics
    metrics = [
        ParticipantMetric(
            participant_id=participant.id,
            metric_code="CODE_QUALITY",
            value=Decimal("8.5"),
            confidence=0.95,
        ),
        ParticipantMetric(
            participant_id=participant.id,
            metric_code="TEAMWORK",
            value=Decimal("7.0"),
            confidence=0.90,
        ),
        ParticipantMetric(
            participant_id=participant.id,
            metric_code="DELIVERY_SPEED",
            value=Decimal("6.5"),
            confidence=0.85,
        ),
    ]
    for metric in metrics:
        db_session.add(metric)

    await db_session.commit()

    # Act: Calculate score
    scoring_service = ScoringService(db=db_session, gemini_client=None)
    result = await scoring_service.calculate_score(
        participant_id=participant.id,
        prof_activity_code=prof_activity.code,
    )

    # Assert: Check result structure
    assert "scoring_result_id" in result
    assert "score_pct" in result
    assert "weight_table_id" in result  # NEW: Should have ID, not version
    assert "weight_table_version" not in result  # OLD: Should NOT have version

    # Assert: Check values
    assert result["weight_table_id"] == str(weight_table.id)
    assert isinstance(result["score_pct"], Decimal)
    assert Decimal("0") <= result["score_pct"] <= Decimal("100")

    # Assert: Check details
    assert len(result["details"]) == 3
    assert result["missing_metrics"] == []

    # Assert: Expected score = (8.5 * 0.40 + 7.0 * 0.30 + 6.5 * 0.30) * 10
    # = (3.4 + 2.1 + 1.95) * 10 = 74.5
    expected_score = Decimal("74.50")
    assert result["score_pct"] == expected_score


@pytest.mark.asyncio
@pytest.mark.integration
async def test_final_report_generation_without_version_field(db_session):
    """
    Test that final report generation works after version field removal (BUG-02).

    AC:
    - GET /api/participants/{id}/final-report returns 200
    - Report contains weight_table_id (not weight_table_version)
    - No AttributeError when generating report
    """
    # Arrange: Create test data
    prof_activity = ProfActivity(
        id=uuid4(),
        code="tester",
        name="Software Tester",
    )
    db_session.add(prof_activity)

    weight_table = WeightTable(
        id=uuid4(),
        prof_activity_id=prof_activity.id,
        weights=[
            {"metric_code": "TEST_COVERAGE", "metric_name": "Test Coverage", "weight": "0.50"},
            {"metric_code": "BUG_DETECTION", "metric_name": "Bug Detection", "weight": "0.50"},
        ],
    )
    db_session.add(weight_table)

    participant = Participant(
        id=uuid4(),
        full_name="Test Tester",
        birth_date=date(1995, 1, 1),
    )
    db_session.add(participant)

    # Add metrics
    metrics = [
        ParticipantMetric(
            participant_id=participant.id,
            metric_code="TEST_COVERAGE",
            value=Decimal("9.0"),
            confidence=0.95,
        ),
        ParticipantMetric(
            participant_id=participant.id,
            metric_code="BUG_DETECTION",
            value=Decimal("8.0"),
            confidence=0.90,
        ),
    ]
    for metric in metrics:
        db_session.add(metric)

    await db_session.commit()

    scoring_service = ScoringService(db=db_session, gemini_client=None)

    # Calculate score to create scoring result
    await scoring_service.calculate_score(
        participant_id=participant.id,
        prof_activity_code=prof_activity.code,
    )

    # Act: Generate final report
    report_data = await scoring_service.generate_final_report(
        participant_id=participant.id,
        prof_activity_code=prof_activity.code,
    )

    # Assert: Check structure
    assert "weight_table_id" in report_data  # NEW: Should have ID
    assert "weight_table_version" not in report_data  # OLD: Should NOT have version

    # Assert: Check value
    assert report_data["weight_table_id"] is not None
    assert isinstance(report_data["weight_table_id"], str)

    # Assert: Check notes contain weight_table reference (by ID, not version)
    assert "weight_table" in report_data["notes"].lower()
    assert report_data["weight_table_id"] in report_data["notes"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_active_weight_table_without_is_active_filter(db_session):
    """
    Test that get_active_weight_table works without is_active field (BUG-02).

    AC:
    - Repository method returns weight table by prof_activity_id only
    - No is_active filter applied (since field was removed)
    """
    from app.repositories.prof_activity import ProfActivityRepository

    # Arrange: Create prof activity and weight table
    prof_activity = ProfActivity(
        id=uuid4(),
        code="test_activity",
        name="Test Activity",
    )
    db_session.add(prof_activity)

    weight_table = WeightTable(
        id=uuid4(),
        prof_activity_id=prof_activity.id,
        weights=[
            {"metric_code": "METRIC_A", "metric_name": "Metric A", "weight": "0.50"},
            {"metric_code": "METRIC_B", "metric_name": "Metric B", "weight": "0.50"},
        ],
    )
    db_session.add(weight_table)
    await db_session.commit()

    # Act: Get active weight table
    repo = ProfActivityRepository(db_session)
    result = await repo.get_active_weight_table(prof_activity.id)

    # Assert: Should return the weight table
    assert result is not None
    assert result.id == weight_table.id
    assert result.prof_activity_id == prof_activity.id

    # Assert: Weight table has no version or is_active attributes
    assert not hasattr(result, "version")
    assert not hasattr(result, "is_active")
