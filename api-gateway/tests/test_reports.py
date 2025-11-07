"""Tests for report upload and download endpoints."""

from io import BytesIO

import pytest
from docx import Document
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Participant, User
from app.services.auth import create_user
from app.core.config import settings


def build_docx_bytes(text: str = "Sample report") -> bytes:
    """Create an in-memory DOCX file for testing."""
    document = Document()
    document.add_paragraph(text)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


@pytest.fixture
async def active_user(db_session: AsyncSession) -> User:
    """Create an active user for authenticated requests."""
    user = await create_user(db_session, "report_user@example.com", "password123", role="USER")
    user.status = "ACTIVE"
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def auth_cookies(client: AsyncClient, active_user: User) -> dict[str, str]:
    """Authenticate and return cookies for the active user."""
    response = await client.post(
        "/api/auth/login",
        json={"email": "report_user@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    cookies = dict(response.cookies)
    client.cookies.clear()
    return cookies


@pytest.fixture
async def sample_participant(db_session: AsyncSession) -> Participant:
    """Create a sample participant for report uploads."""
    participant = Participant(full_name="Report Test", birth_date=None, external_id="RPT-001")
    db_session.add(participant)
    await db_session.commit()
    await db_session.refresh(participant)
    return participant


@pytest.fixture
def reports_storage(tmp_path, monkeypatch):
    """Use a temporary directory for report storage during tests."""
    storage_path = tmp_path / "reports-storage"
    storage_path.mkdir(parents=True)
    monkeypatch.setattr(settings, "file_storage_base", str(storage_path))
    monkeypatch.setattr(settings, "file_storage", "LOCAL")
    return storage_path


@pytest.mark.asyncio
async def test_upload_report_success(
    test_env,
    reports_storage,
    client: AsyncClient,
    auth_cookies: dict[str, str],
    sample_participant: Participant,
):
    """Uploading a valid DOCX report should succeed with 201."""
    payload = build_docx_bytes("Primary report content")

    response = await client.post(
        f"/api/participants/{sample_participant.id}/reports",
        data={"report_type": "REPORT_1"},
        files={"file": ("original.docx", payload, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        cookies=auth_cookies,
    )

    assert response.status_code == 201
    data = response.json()

    assert data["participant_id"] == str(sample_participant.id)
    assert data["type"] == "REPORT_1"
    assert data["status"] == "UPLOADED"
    assert data["etag"]
    assert data["file_ref"]["key"].endswith("original.docx")

    # Ensure file stored on disk
    stored_path = reports_storage / data["file_ref"]["key"]
    assert stored_path.exists()
    assert stored_path.read_bytes() == payload


@pytest.mark.asyncio
async def test_upload_report_invalid_mime_returns_415(
    test_env,
    reports_storage,
    client: AsyncClient,
    auth_cookies: dict[str, str],
    sample_participant: Participant,
):
    """Uploading non-DOCX content should return 415."""
    response = await client.post(
        f"/api/participants/{sample_participant.id}/reports",
        data={"report_type": "REPORT_1"},
        files={"file": ("report.txt", b"plain text", "text/plain")},
        cookies=auth_cookies,
    )

    assert response.status_code == 415


@pytest.mark.asyncio
async def test_upload_report_duplicate_returns_409(
    test_env,
    reports_storage,
    client: AsyncClient,
    auth_cookies: dict[str, str],
    sample_participant: Participant,
):
    """Uploading second report of same type for participant should conflict."""
    payload = build_docx_bytes("First")

    # First upload succeeds
    first = await client.post(
        f"/api/participants/{sample_participant.id}/reports",
        data={"report_type": "REPORT_1"},
        files={"file": ("original.docx", payload, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        cookies=auth_cookies,
    )
    assert first.status_code == 201

    # Second upload with same type should fail
    second = await client.post(
        f"/api/participants/{sample_participant.id}/reports",
        data={"report_type": "REPORT_1"},
        files={"file": ("duplicate.docx", payload, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        cookies=auth_cookies,
    )

    assert second.status_code == 409


@pytest.mark.asyncio
async def test_upload_report_over_limit_returns_413(
    test_env,
    reports_storage,
    client: AsyncClient,
    auth_cookies: dict[str, str],
    sample_participant: Participant,
    monkeypatch,
):
    """Uploading report larger than configured limit should return 413."""
    monkeypatch.setattr(settings, "report_max_size_mb", 1)

    oversized_payload = b"0" * (settings.report_max_size_bytes + 1)

    response = await client.post(
        f"/api/participants/{sample_participant.id}/reports",
        data={"report_type": "REPORT_2"},
        files={"file": ("big.docx", oversized_payload, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        cookies=auth_cookies,
    )

    assert response.status_code == 413


@pytest.mark.asyncio
async def test_download_report_returns_file_with_etag(
    test_env,
    reports_storage,
    client: AsyncClient,
    auth_cookies: dict[str, str],
    sample_participant: Participant,
):
    """Downloading uploaded report should stream file and expose ETag."""
    payload = build_docx_bytes("Download content")

    upload_response = await client.post(
        f"/api/participants/{sample_participant.id}/reports",
        data={"report_type": "REPORT_3"},
        files={"file": ("original.docx", payload, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        cookies=auth_cookies,
    )
    assert upload_response.status_code == 201
    report_id = upload_response.json()["id"]

    download_response = await client.get(
        f"/api/reports/{report_id}/download",
        cookies=auth_cookies,
    )

    assert download_response.status_code == 200
    assert download_response.headers["etag"].startswith("\"")
    assert download_response.headers["etag"].endswith("\"")
    assert "original.docx" in download_response.headers["content-disposition"]
    assert download_response.content == payload

    # Ensure subsequent request with If-None-Match returns 304
    etag_header = download_response.headers["etag"]
    second_response = await client.get(
        f"/api/reports/{report_id}/download",
        headers={"If-None-Match": etag_header},
        cookies=auth_cookies,
    )

    assert second_response.status_code == 304


@pytest.mark.asyncio
async def test_upload_requires_auth(
    test_env,
    reports_storage,
    client: AsyncClient,
    sample_participant: Participant,
):
    """Uploading without authentication should return 401."""
    payload = build_docx_bytes()

    response = await client.post(
        f"/api/participants/{sample_participant.id}/reports",
        data={"report_type": "REPORT_1"},
        files={"file": ("report.docx", payload, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_download_requires_auth(
    test_env,
    reports_storage,
    client: AsyncClient,
    auth_cookies: dict[str, str],
    sample_participant: Participant,
):
    """Downloading without authentication should return 401."""
    payload = build_docx_bytes()

    upload_response = await client.post(
        f"/api/participants/{sample_participant.id}/reports",
        data={"report_type": "REPORT_1"},
        files={"file": ("report.docx", payload, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        cookies=auth_cookies,
    )
    assert upload_response.status_code == 201
    report_id = upload_response.json()["id"]

    download_response = await client.get(f"/api/reports/{report_id}/download")
    assert download_response.status_code == 401
