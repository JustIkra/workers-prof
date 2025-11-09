"""
Pydantic schemas for professional activities.

Defines response DTOs reused across API and services.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class ProfActivityCreateRequest(BaseModel):
    """Request schema for creating a professional activity."""

    code: str = Field(..., min_length=1, max_length=50, description="Unique activity code")
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable name")
    description: str | None = Field(None, description="Optional description")


class ProfActivityUpdateRequest(BaseModel):
    """Request schema for updating a professional activity."""

    name: str | None = Field(None, min_length=1, max_length=255, description="Updated name")
    description: str | None = Field(None, description="Updated description")


class ProfActivityResponse(BaseModel):
    """Response schema for a professional activity."""

    id: UUID
    code: str = Field(..., max_length=50, description="Unique activity code")
    name: str = Field(..., description="Human-readable professional activity name")
    description: str | None = Field(
        None,
        description="Optional description of the professional activity",
    )

    model_config = {"from_attributes": True}


class ProfActivityListResponse(BaseModel):
    """Response schema for list of professional activities."""

    activities: list[ProfActivityResponse] = Field(
        ..., description="List of professional activities"
    )
