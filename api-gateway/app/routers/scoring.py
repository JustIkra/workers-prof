"""
Scoring API router (S2-02, S2-03).

Provides endpoints for:
- Calculating professional fitness scores (S2-02)
- Generating strengths and development areas (S2-03)
"""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user
from app.db.models import User
from app.db.session import get_db
from app.services.scoring import ScoringService

router = APIRouter(prefix="/scoring", tags=["scoring"])


# ===== Schemas =====


class MetricContribution(BaseModel):
    """Individual metric contribution to the score."""

    metric_code: str
    value: str  # Decimal as string
    weight: str  # Decimal as string
    contribution: str  # Decimal as string


class MetricItem(BaseModel):
    """Metric item for strengths/dev_areas (S2-03)."""

    metric_code: str
    metric_name: str
    value: str  # Decimal as string
    weight: str  # Decimal as string


class ScoringResponse(BaseModel):
    """Response schema for scoring calculation (S2-02, S2-03)."""

    scoring_result_id: str
    participant_id: str
    prof_activity_id: str
    prof_activity_name: str
    prof_activity_code: str
    score_pct: Decimal = Field(..., description="Score as percentage (0-100), quantized to 0.01")
    weight_table_version: int
    details: list[MetricContribution]
    missing_metrics: list[str] = Field(default_factory=list)
    strengths: list[MetricItem] = Field(
        default_factory=list, description="Top 5 high-value metrics (S2-03)"
    )
    dev_areas: list[MetricItem] = Field(
        default_factory=list, description="Top 5 low-value metrics (S2-03)"
    )


# ===== Endpoints =====


@router.post("/participants/{participant_id}/calculate", response_model=ScoringResponse)
async def calculate_participant_score(
    participant_id: UUID,
    activity_code: str = Query(..., description="Professional activity code"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Calculate professional fitness score for a participant (S2-02, S2-03).

    Requires:
    - Active weight table for the specified professional activity
    - Extracted metrics for all required metrics in the weight table

    Returns:
    - Score as percentage (0-100)
    - Breakdown of metric contributions
    - Weight table version used
    - Strengths: Top 5 high-value metrics (S2-03)
    - Dev areas: Top 5 low-value metrics (S2-03)

    Raises:
    - 404: Participant or activity not found
    - 400: Missing metrics or invalid data
    """
    scoring_service = ScoringService(db)

    try:
        result = await scoring_service.calculate_score(
            participant_id=participant_id,
            prof_activity_code=activity_code,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return ScoringResponse(
        scoring_result_id=result["scoring_result_id"],
        participant_id=str(participant_id),
        prof_activity_id=result["prof_activity_id"],
        prof_activity_name=result["prof_activity_name"],
        prof_activity_code=activity_code,
        score_pct=result["score_pct"],
        weight_table_version=result["weight_table_version"],
        details=[MetricContribution(**d) for d in result["details"]],
        missing_metrics=result["missing_metrics"],
        strengths=[MetricItem(**item) for item in result.get("strengths", [])],
        dev_areas=[MetricItem(**item) for item in result.get("dev_areas", [])],
    )
