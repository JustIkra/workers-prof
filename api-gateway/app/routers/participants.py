"""
REST API endpoints for participant management.

Provides CRUD operations and search/pagination functionality.
All endpoints require authentication (ACTIVE user).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user
from app.db.models import User
from app.db.session import get_db
from app.repositories.scoring_result import ScoringResultRepository
from app.schemas.final_report import FinalReportResponse
from app.schemas.participant import (
    MessageResponse,
    MetricItem,
    ParticipantCreateRequest,
    ParticipantListResponse,
    ParticipantResponse,
    ParticipantSearchParams,
    ParticipantUpdateRequest,
    ScoringHistoryItem,
    ScoringHistoryResponse,
)
from app.services.participant import ParticipantService
from app.services.scoring import ScoringService

router = APIRouter(prefix="/participants", tags=["participants"])


@router.post("", response_model=ParticipantResponse, status_code=status.HTTP_201_CREATED)
async def create_participant(
    request: ParticipantCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ParticipantResponse:
    """
    Create a new participant.

    Requires: ACTIVE user (any role).

    Request body:
    - full_name: Full name (required, 1-255 chars)
    - birth_date: Birth date (optional)
    - external_id: External ID (optional, max 100 chars)

    Returns: Created participant with UUID and created_at timestamp.
    """
    service = ParticipantService(db)
    return await service.create_participant(request)


@router.get("", response_model=ParticipantListResponse)
async def search_participants(
    query: str | None = Query(None, description="Search by full_name (case-insensitive substring)"),
    external_id: str | None = Query(None, description="Filter by exact external_id match"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ParticipantListResponse:
    """
    Search/list participants with pagination.

    Requires: ACTIVE user (any role).

    Query parameters:
    - query: Substring search on full_name (case-insensitive)
    - external_id: Exact match on external_id
    - page: Page number (default: 1)
    - size: Page size (default: 20, max: 100)

    Results are sorted deterministically by (full_name ASC, id ASC).

    Returns: Paginated list with items, total count, page info.
    """
    params = ParticipantSearchParams(query=query, external_id=external_id, page=page, size=size)
    service = ParticipantService(db)
    return await service.search_participants(params)


@router.get("/{participant_id}", response_model=ParticipantResponse)
async def get_participant(
    participant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ParticipantResponse:
    """
    Get a participant by ID.

    Requires: ACTIVE user (any role).

    Path parameter:
    - participant_id: UUID of the participant

    Returns: Participant details.
    Raises: 404 if participant not found.
    """
    service = ParticipantService(db)
    participant = await service.get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
    return participant


@router.put("/{participant_id}", response_model=ParticipantResponse)
async def update_participant(
    participant_id: UUID,
    request: ParticipantUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ParticipantResponse:
    """
    Update a participant.

    Requires: ACTIVE user (any role).

    Path parameter:
    - participant_id: UUID of the participant

    Request body (all fields optional):
    - full_name: New full name
    - birth_date: New birth date
    - external_id: New external ID

    Returns: Updated participant.
    Raises: 404 if participant not found.
    """
    service = ParticipantService(db)
    participant = await service.update_participant(participant_id, request)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
    return participant


@router.delete("/{participant_id}", response_model=MessageResponse)
async def delete_participant(
    participant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MessageResponse:
    """
    Delete a participant.

    Requires: ACTIVE user (any role).

    Path parameter:
    - participant_id: UUID of the participant

    Returns: Success message.
    Raises: 404 if participant not found.

    Note: Cascades to related reports due to FK constraints.
    """
    service = ParticipantService(db)
    deleted = await service.delete_participant(participant_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
    return MessageResponse(message="Participant deleted successfully")


@router.get("/{participant_id}/final-report", response_model=FinalReportResponse)
async def get_final_report(
    participant_id: UUID,
    activity_code: str = Query(..., description="Professional activity code"),
    format: str = Query("json", description="Response format: 'json' or 'html'"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get final report for a participant (S2-04).

    Returns a complete final report including:
    - Score percentage
    - Strengths (3-5 items)
    - Development areas (3-5 items)
    - Recommendations
    - Detailed metrics table
    - Notes about confidence and algorithm version

    Query parameters:
    - activity_code: Professional activity code (required)
    - format: 'json' (default) or 'html'

    Returns:
    - JSON: FinalReportResponse with all report data
    - HTML: Rendered HTML report (if format=html)

    Raises:
    - 404: Participant or activity not found
    - 400: No scoring result found (calculate score first)
    """
    scoring_service = ScoringService(db)

    try:
        report_data = await scoring_service.generate_final_report(
            participant_id=participant_id,
            prof_activity_code=activity_code,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if format == "html":
        # Import here to avoid circular dependency and only when needed
        from app.services.report_template import render_final_report_html

        html_content = render_final_report_html(report_data)
        return HTMLResponse(content=html_content)

    # Return JSON by default
    return FinalReportResponse(**report_data)


@router.get("/{participant_id}/scores", response_model=ScoringHistoryResponse)
async def get_participant_scoring_history(
    participant_id: UUID,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ScoringHistoryResponse:
    """
    Get scoring history for a participant.

    Returns list of scoring results ordered by computed_at DESC.

    Query parameters:
    - limit: Maximum number of results (default: 10, max: 100)

    Returns:
    - List of scoring results with activity info, scores, strengths, dev_areas
    - Each result includes prof_activity_code for generating final reports

    Raises:
    - 404: Participant not found
    """
    # Verify participant exists
    participant_service = ParticipantService(db)
    participant = await participant_service.get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

    # Get scoring history
    scoring_repo = ScoringResultRepository(db)
    results = await scoring_repo.list_by_participant(participant_id, limit=limit)

    # Transform to response format
    history_items = []
    for result in results:
        # Navigate to prof_activity through weight_table
        prof_activity = result.weight_table.prof_activity

        # Transform strengths/dev_areas if present
        strengths = None
        if result.strengths:
            strengths = [MetricItem(**item) for item in result.strengths]

        dev_areas = None
        if result.dev_areas:
            dev_areas = [MetricItem(**item) for item in result.dev_areas]

        # Extract recommendations (stored as list of dicts or strings)
        recommendations = None
        if result.recommendations:
            # Handle both old format (list of strings) and new format (list of dicts)
            if isinstance(result.recommendations, list):
                if result.recommendations and isinstance(result.recommendations[0], dict):
                    # New format: extract 'text' field from each dict
                    recommendations = [rec.get("text", str(rec)) for rec in result.recommendations]
                else:
                    # Old format: already list of strings
                    recommendations = result.recommendations

        history_items.append(
            ScoringHistoryItem(
                id=result.id,
                prof_activity_code=prof_activity.code,
                prof_activity_name=prof_activity.name,
                score_pct=float(result.score_pct),
                strengths=strengths,
                dev_areas=dev_areas,
                recommendations=recommendations,
                created_at=result.computed_at,
            )
        )

    return ScoringHistoryResponse(results=history_items, total=len(history_items))
