"""
Pydantic schemas for professional activities.

Defines response DTOs reused across API and services.
"""

from uuid import UUID

from pydantic import BaseModel, Field


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
