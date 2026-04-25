"""
AI-HRMS — Auth module Pydantic v2 schemas.
"""

import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ─── Request Schemas ──────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email:    EmailStr = Field(..., description="Registered work or personal email")
    password: str      = Field(..., min_length=1, description="Account password")


class RefreshRequest(BaseModel):
    """Body payload for token refresh (alternative to cookie)."""
    refresh_token: str = Field(..., description="Refresh token issued at login")


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        errors: list[str] = []
        if not any(c.isupper() for c in v):
            errors.append("at least one uppercase letter")
        if not any(c.islower() for c in v):
            errors.append("at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            errors.append("at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in v):
            errors.append("at least one special character")
        if errors:
            raise ValueError("Password must contain: " + ", ".join(errors))
        return v


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token:        str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


# ─── Response Schemas ─────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """Returned in the response body after a successful login / refresh."""
    access_token:  str = Field(..., description="Short-lived JWT access token (15 min)")
    token_type:    str = Field(default="bearer")
    expires_in:    int = Field(..., description="Seconds until the access token expires")


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    module_name: str
    action:      str


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             uuid.UUID
    name:           str
    is_system_role: bool


class UserMeResponse(BaseModel):
    """Full user profile returned by GET /auth/me."""
    model_config = ConfigDict(from_attributes=True)

    id:           uuid.UUID
    email:        str
    first_name:   str
    last_name:    str
    full_name:    str
    avatar_url:   str | None
    tenant_id:    uuid.UUID
    is_superadmin: bool
    roles:        list[RoleOut]
    permissions:  list[PermissionOut]


class LogoutResponse(BaseModel):
    message: str = "Logged out successfully."


class MessageResponse(BaseModel):
    message: str
