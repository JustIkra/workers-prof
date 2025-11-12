"""
Pydantic schemas for AI-generated recommendations (AI-03).

Implements strict JSON schema validation according to
.memory-base/Tech details/infrastructure/prompt-gemini-recommendations.md
"""

from pydantic import BaseModel, Field, field_validator


class StrengthItem(BaseModel):
    """
    Single strength item from recommendations.

    Represents a positive aspect of participant's competencies.
    """

    title: str = Field(
        ...,
        description="Brief title of the strength (max 80 chars)",
        max_length=80,
    )
    metric_codes: list[str] = Field(
        ...,
        description="List of metric codes supporting this strength",
        min_length=1,
    )
    reason: str = Field(
        ...,
        description="Explanation of why this is a strength",
        max_length=200,
    )

    @field_validator("title", "reason")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace."""
        return v.strip()


class DevelopmentAreaItem(BaseModel):
    """
    Single development area item from recommendations.

    Represents an area where participant should improve.
    """

    title: str = Field(
        ...,
        description="Brief title of the development area (max 80 chars)",
        max_length=80,
    )
    metric_codes: list[str] = Field(
        ...,
        description="List of metric codes indicating this area",
        min_length=1,
    )
    actions: list[str] = Field(
        ...,
        description="Concrete actions to improve (max 5 items)",
        max_length=5,
    )

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        """Strip leading/trailing whitespace."""
        return v.strip()

    @field_validator("actions")
    @classmethod
    def strip_actions(cls, v: list[str]) -> list[str]:
        """Strip whitespace from all actions."""
        return [action.strip() for action in v]


class RecommendationItem(BaseModel):
    """
    Single recommendation item (learning guidance).

    Represents a suggested competency focus with actionable advice.
    """

    title: str = Field(
        ...,
        description="Short heading for the recommendation (max 80 chars)",
        max_length=80,
    )
    skill_focus: str = Field(
        ...,
        description="What competency or навык to strengthen (max 120 chars)",
        max_length=120,
    )
    development_advice: str = Field(
        ...,
        description="Actionable tip on how to develop the skill (max 240 chars)",
        max_length=240,
    )
    recommended_formats: list[str] = Field(
        default_factory=list,
        description="Helpful learning formats (≤5 items, each ≤80 chars)",
        max_length=5,
    )

    @field_validator("title", "skill_focus", "development_advice")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace."""
        return v.strip()

    @field_validator("recommended_formats")
    @classmethod
    def validate_formats(cls, value: list[str]) -> list[str]:
        """Trim formats list and enforce length limits."""
        trimmed = [item.strip()[:80] for item in value if item.strip()]
        return trimmed[:5]


class RecommendationsResponse(BaseModel):
    """
    Complete recommendations response from Gemini API.

    This is the schema that Gemini must return, with constraints:
    - strengths: max 5 items
    - dev_areas: max 5 items
    - recommendations: max 5 items
    """

    strengths: list[StrengthItem] = Field(
        ...,
        description="Top strengths (max 5)",
        max_length=5,
    )
    dev_areas: list[DevelopmentAreaItem] = Field(
        ...,
        description="Development areas (max 5)",
        max_length=5,
    )
    recommendations: list[RecommendationItem] = Field(
        ...,
        description="Training recommendations (max 5)",
        max_length=5,
    )

    def to_scoring_result_format(self) -> dict:
        """
        Convert to format suitable for ScoringResult JSONB fields.

        Returns:
            Dictionary with three keys: strengths, dev_areas, recommendations
            Each containing list of dicts for JSONB storage.
        """
        return {
            "strengths": [item.model_dump() for item in self.strengths],
            "dev_areas": [item.model_dump() for item in self.dev_areas],
            "recommendations": [item.model_dump() for item in self.recommendations],
        }


class RecommendationsInput(BaseModel):
    """
    Input data for generating recommendations.

    This is what we send to Gemini API as context.
    """

    context: dict = Field(
        ...,
        description="Context: language, prof_activity, weight_table version",
    )
    metrics: list[dict] = Field(
        ...,
        description="List of metrics with code, name, unit, value, weight",
    )
    score_pct: float = Field(
        ...,
        description="Overall score percentage (0-100)",
        ge=0,
        le=100,
    )
    constraints: dict = Field(
        default={
            "strengths_max": 5,
            "dev_areas_max": 5,
            "recommendations_max": 5,
        },
        description="Constraints for response limits",
    )
