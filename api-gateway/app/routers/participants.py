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
    ParticipantMetricResponse,
    ParticipantMetricsListResponse,
    ParticipantMetricUpdateRequest,
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
                    # New format: return full recommendation objects (AI-09 fix)
                    # Each dict should have: title, link_url, priority
                    recommendations = result.recommendations
                else:
                    # Old format: convert list of strings to list of dicts for compatibility
                    recommendations = [{"title": rec, "link_url": None, "priority": 3} for rec in result.recommendations]

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
                recommendations_status=result.recommendations_status,
                recommendations_error=result.recommendations_error,
            )
        )

    return ScoringHistoryResponse(results=history_items, total=len(history_items))


# ===== Participant Metrics Endpoints (S2-08) =====


@router.get("/{participant_id}/metrics", response_model=ParticipantMetricsListResponse)
async def get_participant_metrics(
    participant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ParticipantMetricsListResponse:
    """
    Get all actual metrics for a participant (S2-08).

    Returns the latest confirmed value for each metric code,
    independent of specific reports.

    Requires: ACTIVE user (any role).

    Returns: List of participant metrics with values, confidence, and update timestamps.
    """
    from datetime import datetime
    from app.repositories.participant_metric import ParticipantMetricRepository
    from app.repositories.metric import MetricDefRepository

    # Check if participant exists
    service = ParticipantService(db)
    participant = await service.get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

    # Get participant metrics actually stored
    metric_repo = ParticipantMetricRepository(db)
    metrics = await metric_repo.list_by_participant(participant_id)

    # Build a map for quick lookup
    by_code = {m.metric_code: m for m in metrics}

    # Ensure full metric coverage: load all defined MetricDefs
    metric_def_repo = MetricDefRepository(db)
    metric_defs = await metric_def_repo.list_all(active_only=True)

    # Compose response list: existing metrics OR synthetic zeros
    response_items: list[ParticipantMetricResponse] = []
    for md in metric_defs:
        existing = by_code.get(md.code)
        if existing:
            response_items.append(ParticipantMetricResponse.model_validate(existing))
        else:
            # Return a synthetic zero-value item for missing metrics
            response_items.append(
                ParticipantMetricResponse(
                    metric_code=md.code,
                    value=0.0,
                    confidence=None,
                    last_source_report_id=None,
                    updated_at=participant.created_at if hasattr(participant, "created_at") else datetime.utcnow(),
                )
            )

    # Debug logging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Returning {len(response_items)} metrics for participant {participant_id} (by_code has {len(by_code)} entries)")

    return ParticipantMetricsListResponse(
        participant_id=participant_id,
        metrics=response_items,
        total=len(response_items),
    )


@router.put(
    "/{participant_id}/metrics/{metric_code}",
    response_model=ParticipantMetricResponse,
)
async def update_participant_metric(
    participant_id: UUID,
    metric_code: str,
    request: ParticipantMetricUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ParticipantMetricResponse:
    """
    Manually update a participant metric value (S2-08).

    Allows admin to manually correct or set metric values.
    This is useful for manual data entry or corrections.

    Requires: ACTIVE user (any role).

    Request body:
    - value: Metric value (range 1-10)
    - confidence: Optional confidence score (0-1)

    Returns: Updated metric with new value and timestamp.
    """
    from decimal import Decimal

    from app.repositories.participant_metric import ParticipantMetricRepository

    # Check if participant exists
    service = ParticipantService(db)
    participant = await service.get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

    # Update metric
    metric_repo = ParticipantMetricRepository(db)
    metric = await metric_repo.update_value(
        participant_id=participant_id,
        metric_code=metric_code,
        value=Decimal(str(request.value)),
        confidence=Decimal(str(request.confidence)) if request.confidence else None,
    )

    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metric '{metric_code}' not found for participant {participant_id}",
        )

    return ParticipantMetricResponse.model_validate(metric)
