"""
Pydantic schemas for Metric operations (S2-01).

Schemas for metric definitions and extracted metrics with validation.
"""

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# ===== MetricDef Schemas =====


class MetricDefBase(BaseModel):
    """Base schema for metric definition."""

    code: str = Field(..., min_length=1, max_length=50, description="Unique metric code")
    name: str = Field(..., min_length=1, max_length=255, description="Metric name")
    description: str | None = Field(None, description="Metric description")
    unit: str | None = Field(None, max_length=50, description="Measurement unit")
    min_value: Decimal | None = Field(None, description="Minimum allowed value")
    max_value: Decimal | None = Field(None, description="Maximum allowed value")
    active: bool = Field(True, description="Whether metric is active")


class MetricDefCreateRequest(MetricDefBase):
    """Request schema for creating a new metric definition."""

    @field_validator("min_value", "max_value")
    @classmethod
    def validate_range(cls, v: Decimal | None, info) -> Decimal | None:
        """Validate that min_value <= max_value if both are provided."""
        if (
            v is not None
            and info.data.get("min_value") is not None
            and info.data.get("max_value") is not None
        ):
            if info.field_name == "max_value" and info.data["min_value"] > v:
                raise ValueError("min_value must be less than or equal to max_value")
        return v


class MetricDefUpdateRequest(BaseModel):
    """Request schema for updating a metric definition."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    unit: str | None = Field(None, max_length=50)
    min_value: Decimal | None = None
    max_value: Decimal | None = None
    active: bool | None = None


class MetricDefResponse(BaseModel):
    """Response schema for metric definition."""

    id: UUID
    code: str
    name: str
    description: str | None
    unit: str | None
    min_value: Decimal | None
    max_value: Decimal | None
    active: bool

    model_config = {"from_attributes": True}


class MetricDefListResponse(BaseModel):
    """Response schema for list of metric definitions."""

    items: list[MetricDefResponse]
    total: int


# ===== ExtractedMetric Schemas =====


class ExtractedMetricBase(BaseModel):
    """Base schema for extracted metric."""

    metric_def_id: UUID = Field(..., description="Metric definition ID")
    value: Decimal = Field(..., description="Extracted value")
    source: Literal["OCR", "LLM", "MANUAL"] = Field("MANUAL", description="Extraction source")
    confidence: Decimal | None = Field(None, ge=0, le=1, description="Confidence score (0-1)")
    notes: str | None = Field(None, description="Additional notes")


class ExtractedMetricCreateRequest(ExtractedMetricBase):
    """Request schema for creating/updating an extracted metric."""

    @field_validator("value")
    @classmethod
    def validate_value_range(cls, v: Decimal) -> Decimal:
        """
        Validate that value is in the expected range [1..10] for most metrics.
        This is a soft validation; actual range checks should be done against metric_def.
        """
        if v < 0:
            raise ValueError("Value must be non-negative")
        return v


class ExtractedMetricUpdateRequest(BaseModel):
    """Request schema for updating an extracted metric."""

    value: Decimal = Field(..., description="Updated value")
    notes: str | None = Field(None, description="Additional notes")


class ExtractedMetricResponse(BaseModel):
    """Response schema for extracted metric."""

    id: UUID
    report_id: UUID
    metric_def_id: UUID
    value: Decimal
    source: str
    confidence: Decimal | None
    notes: str | None

    model_config = {"from_attributes": True}


class ExtractedMetricWithDefResponse(ExtractedMetricResponse):
    """Response schema for extracted metric with metric definition included."""

    metric_def: MetricDefResponse


class ExtractedMetricListResponse(BaseModel):
    """Response schema for list of extracted metrics."""

    items: list[ExtractedMetricWithDefResponse]
    total: int


class ExtractedMetricBulkCreateRequest(BaseModel):
    """Request schema for bulk creating/updating extracted metrics for a report."""

    metrics: list[ExtractedMetricCreateRequest] = Field(
        ..., description="List of metrics to create/update"
    )


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


# ===== Metric Template Schemas =====


class MetricTemplateItem(BaseModel):
    """Schema for a metric template item (metric definition with optional value)."""

    metric_def: MetricDefResponse = Field(..., description="Metric definition")
    value: Decimal | None = Field(None, description="Current value (if already filled)")
    source: str | None = Field(None, description="Source of extraction (if value exists)")
    confidence: Decimal | None = Field(None, description="Confidence score (if value exists)")
    notes: str | None = Field(None, description="Additional notes (if value exists)")


class MetricTemplateResponse(BaseModel):
    """Response schema for metric template - list of all active metrics with optional values."""

    items: list[MetricTemplateItem]
    total: int
    filled_count: int = Field(..., description="Number of metrics that have values")
    missing_count: int = Field(..., description="Number of metrics without values")


# ===== Metric Mapping Schemas =====


class MetricMappingResponse(BaseModel):
    """Response schema for metric label-to-code mapping for a report type."""

    report_type: str = Field(..., description="Report type (e.g., REPORT_1, REPORT_2, REPORT_3)")
    mappings: dict[str, str] = Field(
        ..., description="Dictionary of label (uppercase) -> metric_code mappings"
    )
    total: int = Field(..., description="Total number of mappings")
