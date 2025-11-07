"""
Pydantic schemas for final report (S2-04).

Final report structure based on Product Overview documentation.
Includes JSON schema and versioning support.
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class StrengthItem(BaseModel):
    """Strength item in final report."""

    title: str = Field(..., description="Title of the strength (e.g., 'Коммуникация')")
    metric_codes: list[str] = Field(..., description="Related metric codes")
    reason: str = Field(..., description="Reason/justification for the strength")


class DevAreaItem(BaseModel):
    """Development area item in final report."""

    title: str = Field(..., description="Title of the development area (e.g., 'Планирование')")
    metric_codes: list[str] = Field(..., description="Related metric codes")
    actions: list[str] = Field(..., description="Recommended actions")


class RecommendationItem(BaseModel):
    """Recommendation item in final report."""

    title: str = Field(..., description="Title of the recommendation (e.g., 'Курс по переговорам')")
    link_url: str | None = Field(None, description="URL to the course/resource")
    priority: int = Field(..., ge=1, description="Priority (1 = highest)")


class MetricDetail(BaseModel):
    """Detailed metric information in final report."""

    code: str = Field(..., description="Metric code")
    name: str = Field(..., description="Metric name")
    value: Decimal = Field(..., description="Metric value (1-10)")
    unit: str = Field(default="балл", description="Unit of measurement")
    weight: Decimal = Field(..., description="Weight in calculation (0-1)")
    contribution: Decimal = Field(..., description="Contribution to final score")
    source: Literal["OCR", "LLM", "MANUAL"] = Field(..., description="Source of extraction")
    confidence: Decimal | None = Field(None, description="Confidence level (0-1)")


class FinalReportResponse(BaseModel):
    """
    Final report response schema (S2-04).

    Based on Product Overview/Final report/README.md structure.
    Includes all data needed for JSON and HTML rendering.
    """

    # Header
    participant_id: UUID = Field(..., description="Participant UUID")
    participant_name: str = Field(..., description="Participant full name")
    report_date: datetime = Field(..., description="Report generation date")
    prof_activity_code: str = Field(..., description="Professional activity code")
    prof_activity_name: str = Field(..., description="Professional activity name")
    weight_table_version: int = Field(..., description="Weight table version")

    # Score
    score_pct: Decimal = Field(..., description="Final score percentage (0-100)")

    # Strengths and development areas
    strengths: list[StrengthItem] = Field(default_factory=list, description="3-5 strengths")
    dev_areas: list[DevAreaItem] = Field(default_factory=list, description="3-5 development areas")

    # Recommendations
    recommendations: list[RecommendationItem] = Field(default_factory=list, description="Learning recommendations")

    # Metrics appendix
    metrics: list[MetricDetail] = Field(default_factory=list, description="Full metrics table")

    # Notes
    notes: str | None = Field(None, description="Notes about OCR confidence, algorithm version, etc.")

    # Template version for HTML rendering
    template_version: str = Field(default="1.0.0", description="Report template version")


class FinalReportHtmlResponse(BaseModel):
    """HTML response wrapper for final report."""

    html: str = Field(..., description="Rendered HTML content")
    template_version: str = Field(..., description="Template version used for rendering")
    generated_at: datetime = Field(..., description="HTML generation timestamp")
