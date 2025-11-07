"""
Pydantic schemas for weight tables.

Defines upload payload validation and serialized responses for weight table versions.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class WeightItem(BaseModel):
    """Single metric weight entry within a weight table."""

    metric_code: str = Field(..., min_length=1, max_length=100, description="Metric identifier")
    weight: Decimal = Field(
        ...,
        gt=Decimal("0"),
        le=Decimal("1"),
        description="Weight share for the metric (0 < weight <= 1)",
    )


class WeightTableUploadRequest(BaseModel):
    """Payload for uploading a new weight table version."""

    prof_activity_code: str = Field(
        ..., min_length=1, max_length=50, description="Professional activity code"
    )
    weights: list[WeightItem] = Field(
        ..., description="List of metric weights that must sum to 1.0"
    )
    metadata: dict[str, Any] | None = Field(
        None,
        description="Optional metadata about the weight table (e.g., source, notes)",
    )

    @field_validator("weights")
    @classmethod
    def validate_weights_not_empty(cls, value: list[WeightItem]) -> list[WeightItem]:
        """Ensure weight collection is not empty."""
        if not value:
            raise ValueError("At least one metric weight is required")
        return value

    @model_validator(mode="after")
    def validate_sum_equals_one(self) -> WeightTableUploadRequest:
        """Ensure the sum of weights equals exactly 1.0 (with Decimal precision)."""
        total = sum(item.weight for item in self.weights)
        if total != Decimal("1"):
            raise ValueError("Sum of weights must equal 1.0")
        return self


class WeightItemResponse(BaseModel):
    """Serialized weight entry response."""

    metric_code: str
    weight: Decimal


class WeightTableResponse(BaseModel):
    """Serialized weight table version."""

    id: UUID
    prof_activity_id: UUID
    prof_activity_code: str
    prof_activity_name: str
    version: int
    is_active: bool
    weights: list[WeightItemResponse]
    metadata: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
