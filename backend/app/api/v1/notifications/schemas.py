"""
AI-HRMS — Notifications Pydantic v2 schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing   import Optional
from uuid     import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:           str
    title:        str
    message:      str
    type:         str          # info|success|warning|error
    category:     str          # leave|attendance|payroll|…|general
    action_url:   Optional[str] = None
    action_label: Optional[str] = None
    is_read:      bool
    read_at:      Optional[datetime] = None
    created_at:   datetime


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    unread_count:  int


class MarkReadRequest(BaseModel):
    notification_ids: list[UUID] = Field(..., min_length=1)


class CreateNotificationRequest(BaseModel):
    """Internal use — allows HR/admin to push manual notifications."""
    user_id:      UUID
    title:        str   = Field(..., min_length=1, max_length=200)
    message:      str   = Field(..., min_length=1)
    type:         str   = "info"
    category:     str   = "general"
    action_url:   Optional[str] = None
    action_label: Optional[str] = None
