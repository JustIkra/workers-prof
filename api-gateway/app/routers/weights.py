"""
Weights management router.

Administrative endpoints for uploading, listing, and activating weight tables.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.db.models import User
from app.db.session import get_db
from app.schemas.weight_table import WeightTableResponse, WeightTableUploadRequest
from app.services.weight_table import WeightTableService

router = APIRouter(prefix="/weights", tags=["weights"])


@router.post(
    "/upload",
    response_model=WeightTableResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_weight_table(
    payload: WeightTableUploadRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> WeightTableResponse:
    """
    Upload a new weight table JSON for a professional activity.

    Requires ADMIN role.
    """
    service = WeightTableService(db)
    try:
        return await service.upload_weight_table(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "",
    response_model=list[WeightTableResponse],
    status_code=status.HTTP_200_OK,
)
async def list_weight_tables(
    prof_activity_code: str | None = Query(
        default=None,
        description="Optional professional activity code filter",
    ),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[WeightTableResponse]:
    """
    List weight tables (optionally filtered by professional activity).

    Requires ADMIN role.
    """
    service = WeightTableService(db)
    try:
        return await service.list_weight_tables(prof_activity_code=prof_activity_code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put(
    "/{weight_table_id}",
    response_model=WeightTableResponse,
    status_code=status.HTTP_200_OK,
)
async def update_weight_table(
    weight_table_id: uuid.UUID,
    payload: WeightTableUploadRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> WeightTableResponse:
    """
    Update an existing weight table.

    Requires ADMIN role.
    """
    service = WeightTableService(db)
    try:
        return await service.update_weight_table(weight_table_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
