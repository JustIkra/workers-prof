"""
Tests for ParticipantMetric upsert logic (S2-08).

Tests priority rules:
- More recent report.uploaded_at takes precedence
- On tie, higher confidence value is preferred
"""

import pytest
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from sqlalchemy import select

from app.db.models import Participant, Report, FileRef, ParticipantMetric
from app.repositories.participant_metric import ParticipantMetricRepository


@pytest.mark.unit
async def test_upsert_creates_new_metric(db_session):
    """Test that upsert creates a new metric if it doesn't exist."""
    # Create test participant
    participant = Participant(full_name="Test Participant")
    db_session.add(participant)
    await db_session.commit()
    await db_session.refresh(participant)

    # Create test file_ref and report
    file_ref = FileRef(
        storage="LOCAL",
        bucket="test",
        key="test.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size_bytes=1024,
    )
    db_session.add(file_ref)
    await db_session.commit()

    report = Report(
        participant_id=participant.id,
        type="REPORT_1",
        status="UPLOADED",
        file_ref_id=file_ref.id,
        uploaded_at=datetime.now(UTC),
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    # Upsert metric
    repo = ParticipantMetricRepository(db_session)
    metric = await repo.upsert(
        participant_id=participant.id,
        metric_code="competency_1",
        value=Decimal("7.5"),
        confidence=Decimal("0.95"),
        source_report_id=report.id,
    )

    assert metric.participant_id == participant.id
    assert metric.metric_code == "competency_1"
    assert metric.value == Decimal("7.5")
    assert metric.confidence == Decimal("0.95")
    assert metric.last_source_report_id == report.id


@pytest.mark.unit
async def test_upsert_updates_with_newer_report(db_session):
    """Test that upsert updates metric when new report is more recent."""
    # Create test participant
    participant = Participant(full_name="Test Participant")
    db_session.add(participant)
    await db_session.commit()
    await db_session.refresh(participant)

    # Create first report (older)
    file_ref1 = FileRef(
        storage="LOCAL", bucket="test", key="test1.docx", mime="application/pdf", size_bytes=1024
    )
    db_session.add(file_ref1)
    await db_session.commit()

    report1 = Report(
        participant_id=participant.id,
        type="REPORT_1",
        status="UPLOADED",
        file_ref_id=file_ref1.id,
        uploaded_at=datetime.now(UTC) - timedelta(days=1),  # 1 day ago
    )
    db_session.add(report1)
    await db_session.commit()
    await db_session.refresh(report1)

    # Create second report (newer)
    file_ref2 = FileRef(
        storage="LOCAL", bucket="test", key="test2.docx", mime="application/pdf", size_bytes=1024
    )
    db_session.add(file_ref2)
    await db_session.commit()

    report2 = Report(
        participant_id=participant.id,
        type="REPORT_2",
        status="UPLOADED",
        file_ref_id=file_ref2.id,
        uploaded_at=datetime.now(UTC),  # Today
    )
    db_session.add(report2)
    await db_session.commit()
    await db_session.refresh(report2)

    # Upsert with first report
    repo = ParticipantMetricRepository(db_session)
    metric1 = await repo.upsert(
        participant_id=participant.id,
        metric_code="competency_1",
        value=Decimal("7.5"),
        confidence=Decimal("0.95"),
        source_report_id=report1.id,
    )

    assert metric1.value == Decimal("7.5")
    assert metric1.last_source_report_id == report1.id

    # Upsert with second report (newer) - should update
    metric2 = await repo.upsert(
        participant_id=participant.id,
        metric_code="competency_1",
        value=Decimal("8.2"),
        confidence=Decimal("0.90"),
        source_report_id=report2.id,
    )

    assert metric2.id == metric1.id  # Same metric
    assert metric2.value == Decimal("8.2")  # Updated value
    assert metric2.last_source_report_id == report2.id  # Updated report


@pytest.mark.unit
async def test_upsert_keeps_old_value_with_older_report(db_session):
    """Test that upsert keeps old value when new report is older."""
    # Create test participant
    participant = Participant(full_name="Test Participant")
    db_session.add(participant)
    await db_session.commit()
    await db_session.refresh(participant)

    # Create first report (newer)
    file_ref1 = FileRef(
        storage="LOCAL", bucket="test", key="test1.docx", mime="application/pdf", size_bytes=1024
    )
    db_session.add(file_ref1)
    await db_session.commit()

    report1 = Report(
        participant_id=participant.id,
        type="REPORT_1",
        status="UPLOADED",
        file_ref_id=file_ref1.id,
        uploaded_at=datetime.now(UTC),  # Today
    )
    db_session.add(report1)
    await db_session.commit()
    await db_session.refresh(report1)

    # Create second report (older)
    file_ref2 = FileRef(
        storage="LOCAL", bucket="test", key="test2.docx", mime="application/pdf", size_bytes=1024
    )
    db_session.add(file_ref2)
    await db_session.commit()

    report2 = Report(
        participant_id=participant.id,
        type="REPORT_2",
        status="UPLOADED",
        file_ref_id=file_ref2.id,
        uploaded_at=datetime.now(UTC) - timedelta(days=1),  # 1 day ago
    )
    db_session.add(report2)
    await db_session.commit()
    await db_session.refresh(report2)

    # Upsert with first report (newer)
    repo = ParticipantMetricRepository(db_session)
    metric1 = await repo.upsert(
        participant_id=participant.id,
        metric_code="competency_1",
        value=Decimal("7.5"),
        confidence=Decimal("0.95"),
        source_report_id=report1.id,
    )

    assert metric1.value == Decimal("7.5")
    assert metric1.last_source_report_id == report1.id

    # Upsert with second report (older) - should NOT update
    metric2 = await repo.upsert(
        participant_id=participant.id,
        metric_code="competency_1",
        value=Decimal("8.2"),
        confidence=Decimal("0.90"),
        source_report_id=report2.id,
    )

    assert metric2.id == metric1.id  # Same metric
    assert metric2.value == Decimal("7.5")  # Old value kept
    assert metric2.last_source_report_id == report1.id  # Old report kept


@pytest.mark.unit
async def test_upsert_prefers_higher_confidence_on_same_date(db_session):
    """Test that upsert prefers higher confidence when reports have same timestamp."""
    # Create test participant
    participant = Participant(full_name="Test Participant")
    db_session.add(participant)
    await db_session.commit()
    await db_session.refresh(participant)

    # Create reports with same timestamp
    same_time = datetime.now(UTC)

    file_ref1 = FileRef(
        storage="LOCAL", bucket="test", key="test1.docx", mime="application/pdf", size_bytes=1024
    )
    db_session.add(file_ref1)
    await db_session.commit()

    report1 = Report(
        participant_id=participant.id,
        type="REPORT_1",
        status="UPLOADED",
        file_ref_id=file_ref1.id,
        uploaded_at=same_time,
    )
    db_session.add(report1)
    await db_session.commit()
    await db_session.refresh(report1)

    file_ref2 = FileRef(
        storage="LOCAL", bucket="test", key="test2.docx", mime="application/pdf", size_bytes=1024
    )
    db_session.add(file_ref2)
    await db_session.commit()

    report2 = Report(
        participant_id=participant.id,
        type="REPORT_2",
        status="UPLOADED",
        file_ref_id=file_ref2.id,
        uploaded_at=same_time,
    )
    db_session.add(report2)
    await db_session.commit()
    await db_session.refresh(report2)

    # Upsert with lower confidence
    repo = ParticipantMetricRepository(db_session)
    metric1 = await repo.upsert(
        participant_id=participant.id,
        metric_code="competency_1",
        value=Decimal("7.5"),
        confidence=Decimal("0.80"),
        source_report_id=report1.id,
    )

    assert metric1.value == Decimal("7.5")
    assert metric1.confidence == Decimal("0.80")

    # Upsert with higher confidence - should update
    metric2 = await repo.upsert(
        participant_id=participant.id,
        metric_code="competency_1",
        value=Decimal("8.2"),
        confidence=Decimal("0.95"),
        source_report_id=report2.id,
    )

    assert metric2.id == metric1.id  # Same metric
    assert metric2.value == Decimal("8.2")  # Updated value
    assert metric2.confidence == Decimal("0.95")  # Updated confidence


@pytest.mark.unit
async def test_get_metrics_dict(db_session):
    """Test getting metrics as a dictionary for scoring."""
    # Create test participant
    participant = Participant(full_name="Test Participant")
    db_session.add(participant)
    await db_session.commit()
    await db_session.refresh(participant)

    # Create report
    file_ref = FileRef(
        storage="LOCAL", bucket="test", key="test.docx", mime="application/pdf", size_bytes=1024
    )
    db_session.add(file_ref)
    await db_session.commit()

    report = Report(
        participant_id=participant.id,
        type="REPORT_1",
        status="UPLOADED",
        file_ref_id=file_ref.id,
        uploaded_at=datetime.now(UTC),
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    # Upsert multiple metrics
    repo = ParticipantMetricRepository(db_session)
    await repo.upsert(
        participant_id=participant.id,
        metric_code="competency_1",
        value=Decimal("7.5"),
        confidence=Decimal("0.95"),
        source_report_id=report.id,
    )
    await repo.upsert(
        participant_id=participant.id,
        metric_code="competency_2",
        value=Decimal("8.2"),
        confidence=Decimal("0.90"),
        source_report_id=report.id,
    )

    # Get metrics dict
    metrics_dict = await repo.get_metrics_dict(participant.id)

    assert len(metrics_dict) == 2
    assert metrics_dict["competency_1"] == Decimal("7.5")
    assert metrics_dict["competency_2"] == Decimal("8.2")


@pytest.mark.unit
async def test_manual_update_value(db_session):
    """Test manual update of metric value."""
    # Create test participant
    participant = Participant(full_name="Test Participant")
    db_session.add(participant)
    await db_session.commit()
    await db_session.refresh(participant)

    # Create report
    file_ref = FileRef(
        storage="LOCAL", bucket="test", key="test.docx", mime="application/pdf", size_bytes=1024
    )
    db_session.add(file_ref)
    await db_session.commit()

    report = Report(
        participant_id=participant.id,
        type="REPORT_1",
        status="UPLOADED",
        file_ref_id=file_ref.id,
        uploaded_at=datetime.now(UTC),
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    # Create metric
    repo = ParticipantMetricRepository(db_session)
    metric = await repo.upsert(
        participant_id=participant.id,
        metric_code="competency_1",
        value=Decimal("7.5"),
        confidence=Decimal("0.95"),
        source_report_id=report.id,
    )

    assert metric.value == Decimal("7.5")

    # Manual update
    updated = await repo.update_value(
        participant_id=participant.id, metric_code="competency_1", value=Decimal("9.0")
    )

    assert updated.id == metric.id
    assert updated.value == Decimal("9.0")
    assert updated.confidence == Decimal("0.95")  # Kept old confidence
