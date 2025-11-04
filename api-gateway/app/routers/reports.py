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
