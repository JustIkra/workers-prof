"""
Pydantic schemas for authentication endpoints.

Defines request/response models for register, login, and user management.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ===== Request Schemas =====
class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=100, description="User password")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Validate password strength.

        Requirements:
        - At least 8 characters
        - Contains at least one letter and one digit
        """
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    model_config = {
        "json_schema_extra": {"example": {"email": "user@example.com", "password": "password123"}}
    }


class LoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    model_config = {
        "json_schema_extra": {"example": {"email": "user@example.com", "password": "password123"}}
    }


class ApproveUserRequest(BaseModel):
    """Request schema for admin to approve a pending user."""

    user_id: UUID = Field(..., description="UUID of the user to approve")

    model_config = {
        "json_schema_extra": {"example": {"user_id": "123e4567-e89b-12d3-a456-426614174000"}}
    }


# ===== Response Schemas =====
class UserResponse(BaseModel):
    """Response schema for user data."""

    id: UUID
    email: str
    role: str
    status: str
    created_at: datetime
    approved_at: datetime | None = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Response schema for login (token set in httpOnly cookie)."""

    message: str = Field(..., description="Success message")
    user: UserResponse

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Login successful",
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "user@example.com",
                    "role": "USER",
                    "status": "ACTIVE",
                    "created_at": "2025-01-15T12:00:00Z",
                    "approved_at": "2025-01-15T12:30:00Z",
                },
            }
        }
    }


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str

    model_config = {
        "json_schema_extra": {"example": {"message": "Operation completed successfully"}}
    }
