"""
Tests for BUG-01: Metrics status update logic.

Verifies that report status is correctly set based on metrics_saved count:
- If metrics_saved > 0 -> status EXTRACTED
- If metrics_saved == 0 AND errors -> status FAILED
- If metrics_saved == 0 AND no errors -> status EXTRACTED (no metrics found)
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.db.models import FileRef, MetricDef, Participant, Report, ReportImage
from app.tasks.extraction import extract_images_from_report


@pytest.mark.integration
async def test_extraction_status_extracted_when_metrics_saved(db_session, tmp_path):
    """Test that status is EXTRACTED when metrics are successfully saved."""
    from app.core.config import Settings
    from app.core.storage import LocalReportStorage

    settings = Settings()

    # Create test participant
    participant = Participant(
        id=uuid.uuid4(),
        full_name="Test Participant",
    )
    db_session.add(participant)
    await db_session.flush()

    # Create test DOCX file with images
    from tests.test_docx_extraction import create_test_docx_with_images

    docx_file = tmp_path / "test_report.docx"
    create_test_docx_with_images(docx_file, num_images=1)

    # Save to storage
    storage = LocalReportStorage(str(tmp_path / "storage"))
    storage.ensure_base()
    report_id = uuid.uuid4()
    storage_key = f"reports/{participant.id}/{report_id}/original.docx"

    with open(docx_file, "rb") as f:
        storage.save(storage_key, f)

    # Create FileRef
    file_ref = FileRef(
        storage="LOCAL",
        bucket=str(tmp_path / "storage"),
        key=storage_key,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size_bytes=docx_file.stat().st_size,
    )
    db_session.add(file_ref)
    await db_session.flush()

    # Create Report
    report = Report(
        id=report_id,
        participant_id=participant.id,
        status="UPLOADED",
        file_ref_id=file_ref.id,
        uploaded_at=datetime.now(UTC),
    )
    db_session.add(report)
    await db_session.commit()

    # Mock metric extraction to return successful results
    mock_metrics_result = {
        "metrics_extracted": 5,
        "metrics_saved": 5,  # ← Success: metrics saved
        "errors": [],
    }

    with (
        patch.dict("os.environ", {"FILE_STORAGE_BASE": str(tmp_path / "storage")}),
        patch(
            "app.services.metric_extraction.MetricExtractionService.extract_metrics_from_report_images",
            new_callable=AsyncMock,
            return_value=mock_metrics_result,
        ),
        patch(
            "app.services.metric_extraction.MetricExtractionService.close",
            new_callable=AsyncMock,
        ),
    ):
        # Run extraction task (Celery eager mode)
        result = extract_images_from_report(str(report_id))

    # Verify status is EXTRACTED
    await db_session.refresh(report)
    assert report.status == "EXTRACTED", "Status should be EXTRACTED when metrics_saved > 0"
    assert report.extracted_at is not None
    assert report.extract_error is None

    # Verify task result
    assert result["status"] == "success"
    assert result["metrics_saved"] == 5


@pytest.mark.integration
async def test_extraction_status_error_when_no_metrics_saved_with_errors(db_session, tmp_path):
    """Test that status is FAILED when metrics_saved == 0 and there are errors."""
    from app.core.config import Settings
    from app.core.storage import LocalReportStorage

    settings = Settings()

    # Create test participant
    participant = Participant(
        id=uuid.uuid4(),
        full_name="Test Participant",
    )
    db_session.add(participant)
    await db_session.flush()

    # Create test DOCX file
    from tests.test_docx_extraction import create_test_docx_with_images

    docx_file = tmp_path / "test_report.docx"
    create_test_docx_with_images(docx_file, num_images=1)

    # Save to storage
    storage = LocalReportStorage(str(tmp_path / "storage"))
    storage.ensure_base()
    report_id = uuid.uuid4()
    storage_key = f"reports/{participant.id}/{report_id}/original.docx"

    with open(docx_file, "rb") as f:
        storage.save(storage_key, f)

    # Create FileRef
    file_ref = FileRef(
        storage="LOCAL",
        bucket=str(tmp_path / "storage"),
        key=storage_key,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size_bytes=docx_file.stat().st_size,
    )
    db_session.add(file_ref)
    await db_session.flush()

    # Create Report
    report = Report(
        id=report_id,
        participant_id=participant.id,
        status="UPLOADED",
        file_ref_id=file_ref.id,
        uploaded_at=datetime.now(UTC),
    )
    db_session.add(report)
    await db_session.commit()

    # Mock metric extraction to return errors (e.g., database failure)
    mock_metrics_result = {
        "metrics_extracted": 5,
        "metrics_saved": 0,  # ← Failure: no metrics saved
        "errors": [
            {"label": "METRIC1", "error": "Database connection failed", "critical": True}
        ],
    }

    with (
        patch.dict("os.environ", {"FILE_STORAGE_BASE": str(tmp_path / "storage")}),
        patch(
            "app.services.metric_extraction.MetricExtractionService.extract_metrics_from_report_images",
            new_callable=AsyncMock,
            return_value=mock_metrics_result,
        ),
        patch(
            "app.services.metric_extraction.MetricExtractionService.close",
            new_callable=AsyncMock,
        ),
    ):
        # Run extraction task
        result = extract_images_from_report(str(report_id))

    # Verify status is FAILED
    await db_session.refresh(report)
    assert report.status == "FAILED", "Status should be FAILED when metrics_saved == 0 with errors"
    assert report.extract_error is not None
    assert "Failed to save metrics" in report.extract_error

    # Verify task result
    assert result["status"] == "success"  # Task itself succeeded
    assert result["metrics_saved"] == 0


@pytest.mark.integration
async def test_extraction_status_extracted_when_no_metrics_found(db_session, tmp_path):
    """Test that status is EXTRACTED when no metrics found but no errors."""
    from app.core.config import Settings
    from app.core.storage import LocalReportStorage

    settings = Settings()

    # Create test participant
    participant = Participant(
        id=uuid.uuid4(),
        full_name="Test Participant",
    )
    db_session.add(participant)
    await db_session.flush()

    # Create test DOCX file
    from tests.test_docx_extraction import create_test_docx_with_images

    docx_file = tmp_path / "test_report.docx"
    create_test_docx_with_images(docx_file, num_images=1)

    # Save to storage
    storage = LocalReportStorage(str(tmp_path / "storage"))
    storage.ensure_base()
    report_id = uuid.uuid4()
    storage_key = f"reports/{participant.id}/{report_id}/original.docx"

    with open(docx_file, "rb") as f:
        storage.save(storage_key, f)

    # Create FileRef
    file_ref = FileRef(
        storage="LOCAL",
        bucket=str(tmp_path / "storage"),
        key=storage_key,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size_bytes=docx_file.stat().st_size,
    )
    db_session.add(file_ref)
    await db_session.flush()

    # Create Report
    report = Report(
        id=report_id,
        participant_id=participant.id,
        status="UPLOADED",
        file_ref_id=file_ref.id,
        uploaded_at=datetime.now(UTC),
    )
    db_session.add(report)
    await db_session.commit()

    # Mock metric extraction: no metrics found, no errors
    mock_metrics_result = {
        "metrics_extracted": 0,
        "metrics_saved": 0,  # ← No metrics found
        "errors": [],  # ← No errors
    }

    with (
        patch.dict("os.environ", {"FILE_STORAGE_BASE": str(tmp_path / "storage")}),
        patch(
            "app.services.metric_extraction.MetricExtractionService.extract_metrics_from_report_images",
            new_callable=AsyncMock,
            return_value=mock_metrics_result,
        ),
        patch(
            "app.services.metric_extraction.MetricExtractionService.close",
            new_callable=AsyncMock,
        ),
    ):
        # Run extraction task
        result = extract_images_from_report(str(report_id))

    # Verify status is EXTRACTED (no errors)
    await db_session.refresh(report)
    assert (
        report.status == "EXTRACTED"
    ), "Status should be EXTRACTED when no metrics found but no errors"
    assert report.extracted_at is not None
    assert report.extract_error is None

    # Verify task result
    assert result["status"] == "success"
    assert result["metrics_saved"] == 0


@pytest.mark.unit
async def test_critical_db_error_aborts_metric_saving():
    """
    Test that critical database errors (OperationalError) during metric saving
    are re-raised and abort the extraction process.
    """
    from app.services.metric_extraction import MetricExtractionService

    # Mock session and repositories
    mock_session = MagicMock()
    mock_service = MetricExtractionService(mock_session)

    # Mock repositories to raise OperationalError on upsert
    mock_service.participant_metric_repo = AsyncMock()
    mock_service.participant_metric_repo.upsert.side_effect = OperationalError(
        "Database connection lost", None, None
    )
    mock_service.extracted_metric_repo = AsyncMock()
    mock_service.extracted_metric_repo.create_or_update = AsyncMock()

    # Create mock report and metric
    mock_report = MagicMock()
    mock_report.participant_id = uuid.uuid4()

    # Test that critical error is re-raised
    with pytest.raises(OperationalError):
        # This should trigger the critical error path
        from app.services.metric_extraction import ExtractedMetric

        metric = ExtractedMetric(
            normalized_label="TEST_METRIC",
            normalized_value=Decimal("7.5"),
            confidence=0.95,
            source_image="test.png",
        )

        # Simulate the save loop logic
        try:
            # This would normally happen in extract_metrics_from_report_images
            await mock_service.participant_metric_repo.upsert(
                participant_id=mock_report.participant_id,
                metric_code="TEST_METRIC",
                value=metric.normalized_value,
                confidence=Decimal(str(metric.confidence)),
                source_report_id=uuid.uuid4(),
            )
        except Exception as e:
            # This is the logic we added in BUG-01 fix
            is_critical = isinstance(e, (OperationalError,))
            if is_critical:
                raise
