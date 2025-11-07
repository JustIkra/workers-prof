"""
Tests for DOCX image extraction functionality.

Tests cover:
- Extracting images from DOCX files
- Report status transitions (UPLOADED -> EXTRACTED/FAILED)
- Storage of extracted images
- Creation of ReportImage records
"""

import io
import uuid
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FileRef, Participant, Report, ReportImage
from app.services.docx_extraction import (
    DocxImageExtractor,
    ExtractedImage,
    InvalidDocxError,
)


def create_test_docx_with_images(path: Path, num_images: int = 2) -> None:
    """
    Create a test DOCX file with embedded images.

    Args:
        path: Where to save the DOCX file
        num_images: Number of test images to embed
    """
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as docx_zip:
        # Add minimal DOCX structure
        docx_zip.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
</Types>""",
        )

        docx_zip.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""",
        )

        docx_zip.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:t>Test document with images</w:t></w:p>
  </w:body>
</w:document>""",
        )

        # Add test images to word/media/
        for i in range(num_images):
            # Create a simple test image
            img = Image.new("RGB", (100, 100), color=(255, 0, 0))
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            img_bytes.seek(0)

            docx_zip.writestr(f"word/media/image{i+1}.png", img_bytes.read())


class TestDocxImageExtractor:
    """Test the DOCX image extraction service."""

    def test_extract_images__valid_docx__returns_images(self, tmp_path):
        """Test extracting images from a valid DOCX file."""
        # Create a test DOCX file with 3 images
        docx_file = tmp_path / "test.docx"
        create_test_docx_with_images(docx_file, num_images=3)

        extractor = DocxImageExtractor()
        images = extractor.extract_images(docx_file)

        assert len(images) == 3
        assert all(isinstance(img, ExtractedImage) for img in images)
        assert images[0].order_index == 0
        assert images[1].order_index == 1
        assert images[2].order_index == 2
        assert all(img.format == "PNG" for img in images)
        assert all(img.page == 0 for img in images)  # DOCX has no page concept
        assert all(img.size_bytes > 0 for img in images)

    def test_extract_images__no_images__returns_empty_list(self, tmp_path):
        """Test extracting from DOCX with no images."""
        docx_file = tmp_path / "empty.docx"
        create_test_docx_with_images(docx_file, num_images=0)

        extractor = DocxImageExtractor()
        images = extractor.extract_images(docx_file)

        assert images == []

    def test_extract_images__invalid_file__raises_error(self, tmp_path):
        """Test that invalid DOCX raises InvalidDocxError."""
        extractor = DocxImageExtractor()

        # Create a non-DOCX file
        invalid_file = tmp_path / "test.txt"
        invalid_file.write_text("Not a DOCX file")

        with pytest.raises(InvalidDocxError):
            extractor.extract_images(invalid_file)

    def test_extract_images__nonexistent_file__raises_error(self):
        """Test that nonexistent file raises InvalidDocxError."""
        extractor = DocxImageExtractor()
        nonexistent = Path("/nonexistent/file.docx")

        with pytest.raises(InvalidDocxError):
            extractor.extract_images(nonexistent)

    def test_convert_to_png__valid_image__converts_successfully(self):
        """Test converting image data to PNG format."""
        extractor = DocxImageExtractor()

        # Create a test JPEG image
        img = Image.new("RGB", (50, 50), color=(0, 255, 0))
        jpeg_bytes = io.BytesIO()
        img.save(jpeg_bytes, format="JPEG")
        jpeg_data = jpeg_bytes.getvalue()

        # Convert to PNG
        png_data = extractor.convert_to_png(jpeg_data)

        # Verify it's valid PNG
        with Image.open(io.BytesIO(png_data)) as result_img:
            assert result_img.format == "PNG"
            assert result_img.size == (50, 50)

    def test_convert_to_png__rgba_image__handles_transparency(self):
        """Test converting RGBA image preserves transparency correctly."""
        extractor = DocxImageExtractor()

        # Create RGBA image with transparency
        img = Image.new("RGBA", (50, 50), color=(0, 0, 255, 128))
        rgba_bytes = io.BytesIO()
        img.save(rgba_bytes, format="PNG")
        rgba_data = rgba_bytes.getvalue()

        # Convert (should convert to RGB with white background)
        png_data = extractor.convert_to_png(rgba_data)

        # Verify it's valid PNG and RGB mode
        with Image.open(io.BytesIO(png_data)) as result_img:
            assert result_img.format == "PNG"
            assert result_img.mode == "RGB"


@pytest.mark.asyncio
class TestReportImageExtraction:
    """Integration tests for report image extraction."""

    async def test_extract_report__uploaded_status__updates_to_extracted(
        self,
        db_session: AsyncSession,
        tmp_path,
    ):
        """Test that extraction updates report status to EXTRACTED."""
        from app.core.config import Settings
        from app.services.storage import LocalReportStorage
        from app.tasks.extraction import extract_images_from_report

        settings = Settings()

        # Create test participant
        participant = Participant(
            id=uuid.uuid4(),
            full_name="Test Participant",
        )
        db_session.add(participant)
        await db_session.flush()

        # Create test DOCX file
        docx_file = tmp_path / "test_report.docx"
        create_test_docx_with_images(docx_file, num_images=2)

        # Save to storage
        storage = LocalReportStorage(str(tmp_path / "storage"))
        storage.ensure_base()
        report_id = uuid.uuid4()
        storage_key = f"reports/{participant.id}/{report_id}/original.docx"
        storage_path = storage.resolve_path(storage_key)
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_bytes(docx_file.read_bytes())

        # Create FileRef
        file_ref = FileRef(
            id=uuid.uuid4(),
            storage="LOCAL",
            bucket="local",
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
            type="REPORT_1",
            status="UPLOADED",
            file_ref_id=file_ref.id,
        )
        db_session.add(report)
        await db_session.commit()

        # Mock settings for task
        with patch("app.tasks.extraction.settings") as mock_settings:
            mock_settings.postgres_dsn = settings.postgres_dsn
            mock_settings.file_storage_base = str(tmp_path / "storage")

            # Execute extraction task (eager mode)
            result = extract_images_from_report(str(report_id))

        # Verify results
        assert result["status"] == "success"
        assert result["images_extracted"] == 2

        # Reload report
        await db_session.refresh(report)
        assert report.status == "EXTRACTED"
        assert report.extracted_at is not None
        assert report.extract_error is None

        # Verify ReportImage records
        stmt = select(ReportImage).where(ReportImage.report_id == report_id)
        result = await db_session.execute(stmt)
        images = result.scalars().all()
        assert len(images) == 2

    async def test_extract_report__invalid_docx__updates_to_failed(
        self,
        db_session: AsyncSession,
        tmp_path,
    ):
        """Test that failed extraction updates report status to FAILED."""
        from app.core.config import Settings
        from app.services.storage import LocalReportStorage
        from app.tasks.extraction import extract_images_from_report

        settings = Settings()

        # Create test participant
        participant = Participant(
            id=uuid.uuid4(),
            full_name="Test Participant",
        )
        db_session.add(participant)
        await db_session.flush()

        # Create invalid DOCX file (plain text)
        invalid_file = tmp_path / "invalid.docx"
        invalid_file.write_text("Not a valid DOCX")

        # Save to storage
        storage = LocalReportStorage(str(tmp_path / "storage"))
        storage.ensure_base()
        report_id = uuid.uuid4()
        storage_key = f"reports/{participant.id}/{report_id}/original.docx"
        storage_path = storage.resolve_path(storage_key)
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_bytes(invalid_file.read_bytes())

        # Create FileRef
        file_ref = FileRef(
            id=uuid.uuid4(),
            storage="LOCAL",
            bucket="local",
            key=storage_key,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            size_bytes=invalid_file.stat().st_size,
        )
        db_session.add(file_ref)
        await db_session.flush()

        # Create Report
        report = Report(
            id=report_id,
            participant_id=participant.id,
            type="REPORT_1",
            status="UPLOADED",
            file_ref_id=file_ref.id,
        )
        db_session.add(report)
        await db_session.commit()

        # Mock settings for task
        with patch("app.tasks.extraction.settings") as mock_settings:
            mock_settings.postgres_dsn = settings.postgres_dsn
            mock_settings.file_storage_base = str(tmp_path / "storage")

            # Execute extraction task (should fail)
            result = extract_images_from_report(str(report_id))

        # Verify error was handled
        assert result["status"] == "failed"
        assert "error" in result

        # Reload report
        await db_session.refresh(report)
        assert report.status == "FAILED"
        assert report.extract_error is not None

    async def test_extract_report__creates_report_image_records(
        self,
        db_session: AsyncSession,
        tmp_path,
    ):
        """Test that extraction creates ReportImage records with correct metadata."""
        from app.core.config import Settings
        from app.services.storage import LocalReportStorage
        from app.tasks.extraction import extract_images_from_report

        settings = Settings()

        # Create test participant
        participant = Participant(
            id=uuid.uuid4(),
            full_name="Test Participant",
        )
        db_session.add(participant)
        await db_session.flush()

        # Create test DOCX file with 3 images
        docx_file = tmp_path / "test_report.docx"
        create_test_docx_with_images(docx_file, num_images=3)

        # Save to storage
        storage = LocalReportStorage(str(tmp_path / "storage"))
        storage.ensure_base()
        report_id = uuid.uuid4()
        storage_key = f"reports/{participant.id}/{report_id}/original.docx"
        storage_path = storage.resolve_path(storage_key)
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_bytes(docx_file.read_bytes())

        # Create FileRef and Report
        file_ref = FileRef(
            id=uuid.uuid4(),
            storage="LOCAL",
            bucket="local",
            key=storage_key,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            size_bytes=docx_file.stat().st_size,
        )
        db_session.add(file_ref)
        await db_session.flush()

        report = Report(
            id=report_id,
            participant_id=participant.id,
            type="REPORT_1",
            status="UPLOADED",
            file_ref_id=file_ref.id,
        )
        db_session.add(report)
        await db_session.commit()

        # Execute extraction
        with patch("app.tasks.extraction.settings") as mock_settings:
            mock_settings.postgres_dsn = settings.postgres_dsn
            mock_settings.file_storage_base = str(tmp_path / "storage")
            extract_images_from_report(str(report_id))

        # Verify ReportImage records
        stmt = (
            select(ReportImage)
            .where(ReportImage.report_id == report_id)
            .order_by(ReportImage.order_index)
        )
        result = await db_session.execute(stmt)
        images = result.scalars().all()

        assert len(images) == 3
        for i, img in enumerate(images):
            assert img.kind == "TABLE"
            assert img.page == 0
            assert img.order_index == i
            assert img.file_ref_id is not None

            # Verify image file exists
            stmt = select(FileRef).where(FileRef.id == img.file_ref_id)
            result = await db_session.execute(stmt)
            img_file_ref = result.scalar_one()
            img_path = storage.resolve_path(img_file_ref.key)
            assert img_path.exists()
            assert img_file_ref.mime == "image/png"


@pytest.mark.asyncio
class TestExtractionEndpoint:
    """Tests for POST /reports/{id}/extract endpoint."""

    async def test_extract_endpoint__valid_report__returns_accepted(
        self,
        client,
        db_session: AsyncSession,
        active_user_token: str,
        tmp_path,
    ):
        """Test that extract endpoint returns 202 Accepted and queues task."""
        from app.services.storage import LocalReportStorage

        # Create test participant
        participant = Participant(
            id=uuid.uuid4(),
            full_name="Test Participant",
        )
        db_session.add(participant)
        await db_session.flush()

        # Create test DOCX file
        docx_file = tmp_path / "test_report.docx"
        create_test_docx_with_images(docx_file, num_images=2)

        # Save to storage
        storage = LocalReportStorage(str(tmp_path / "storage"))
        storage.ensure_base()
        report_id = uuid.uuid4()
        storage_key = f"reports/{participant.id}/{report_id}/original.docx"
        storage_path = storage.resolve_path(storage_key)
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_bytes(docx_file.read_bytes())

        # Create FileRef and Report
        file_ref = FileRef(
            id=uuid.uuid4(),
            storage="LOCAL",
            bucket="local",
            key=storage_key,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            size_bytes=docx_file.stat().st_size,
        )
        db_session.add(file_ref)
        await db_session.flush()

        report = Report(
            id=report_id,
            participant_id=participant.id,
            type="REPORT_1",
            status="UPLOADED",
            file_ref_id=file_ref.id,
        )
        db_session.add(report)
        await db_session.commit()

        # Call extract endpoint
        headers = {"Authorization": f"Bearer {active_user_token}"}
        response = await client.post(
            f"/api/reports/{report_id}/extract",
            headers=headers,
        )

        # Verify response
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert data["report_id"] == str(report_id)
        assert "task_id" in data
        assert data["message"] == "Extraction task started"

    async def test_extract_endpoint__nonexistent_report__returns_404(
        self,
        client,
        active_user_token: str,
    ):
        """Test that extract endpoint returns 404 for nonexistent report."""
        nonexistent_id = uuid.uuid4()

        headers = {"Authorization": f"Bearer {active_user_token}"}
        response = await client.post(
            f"/api/reports/{nonexistent_id}/extract",
            headers=headers,
        )

        assert response.status_code == 404

    async def test_extract_endpoint__unauthenticated__returns_401(
        self,
        client,
        db_session: AsyncSession,
    ):
        """Test that extract endpoint requires authentication."""
        # Create dummy report
        participant = Participant(
            id=uuid.uuid4(),
            full_name="Test Participant",
        )
        db_session.add(participant)
        await db_session.flush()

        file_ref = FileRef(
            id=uuid.uuid4(),
            storage="LOCAL",
            bucket="local",
            key="test/key",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            size_bytes=1000,
        )
        db_session.add(file_ref)
        await db_session.flush()

        report = Report(
            id=uuid.uuid4(),
            participant_id=participant.id,
            type="REPORT_1",
            status="UPLOADED",
            file_ref_id=file_ref.id,
        )
        db_session.add(report)
        await db_session.commit()

        # Call without auth header
        response = await client.post(f"/api/reports/{report.id}/extract")

        assert response.status_code == 401
