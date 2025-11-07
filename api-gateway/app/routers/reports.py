"""
Report upload and download endpoints.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.report import ReportType, ReportUploadResponse
from app.services.report import ReportService
from app.tasks.extraction import extract_images_from_report

router = APIRouter(tags=["reports"])


@router.post(
    "/participants/{participant_id}/reports",
    response_model=ReportUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_report(
    participant_id: UUID,
    report_type: ReportType = Form(..., description="Report type (REPORT_1/REPORT_2/REPORT_3)"),
    file: UploadFile = File(..., description="DOCX report file"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ReportUploadResponse:
    """
    Upload a DOCX report for a participant.

    Requires active authentication.
    """
    service = ReportService(db)
    return await service.upload_report(participant_id, report_type, file)


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Download original DOCX report.

    Returns 304 when If-None-Match matches stored ETag.
    """
    service = ReportService(db)
    context = await service.get_download_context(report_id)

    if ReportService.matches_etag(request.headers.get("if-none-match"), context.etag):
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)

    headers = {"ETag": ReportService.format_etag(context.etag)}

    return FileResponse(
        path=context.path,
        media_type=context.mime,
        filename=context.filename,
        headers=headers,
    )


@router.post(
    "/reports/{report_id}/extract",
    status_code=status.HTTP_202_ACCEPTED,
)
async def extract_report(
    report_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """
    Start extraction of images from a DOCX report.

    Returns immediately with task ID. Extraction happens asynchronously.
    Report status will be updated to EXTRACTED or FAILED when complete.

    Requires active authentication.
    """
    service = ReportService(db)

    # Verify report exists and belongs to accessible participant
    report = await service.get_report_by_id(report_id)

    # Queue extraction task
    request_id = getattr(request.state, "request_id", None)
    task = extract_images_from_report.delay(str(report_id), request_id=request_id)

    return {
        "report_id": str(report_id),
        "task_id": task.id,
        "status": "accepted",
        "message": "Extraction task started",
    }
