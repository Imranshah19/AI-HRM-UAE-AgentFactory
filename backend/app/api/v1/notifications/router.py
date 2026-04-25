"""
AI-HRMS — Notifications router.

GET    /notifications                 → last 50 for current user
GET    /notifications/unread-count    → integer count
POST   /notifications/mark-read       → mark specific IDs read
POST   /notifications/mark-all-read   → mark all read
POST   /notifications                 → create manual notification (admin only)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_permission
from app.models.tenant import User

from app.api.v1.notifications import service
from app.api.v1.notifications.schemas import (
    CreateNotificationRequest,
    MarkReadRequest,
    NotificationListResponse,
    NotificationResponse,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="Get last 50 notifications for the current user",
)
async def list_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    notifications = await service.get_notifications(
        current_user.tenant_id, current_user.id, db
    )
    unread_count = sum(1 for n in notifications if not n.is_read)
    return NotificationListResponse(
        notifications=notifications,
        unread_count=unread_count,
    )


@router.get(
    "/unread-count",
    response_model=dict,
    summary="Get unread notification count",
)
async def unread_count(
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    count = await service.get_unread_count(current_user.tenant_id, current_user.id, db)
    return {"unread_count": count}


@router.post(
    "/mark-read",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    summary="Mark specific notifications as read",
)
async def mark_read(
    body:         MarkReadRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    updated = await service.mark_as_read(
        current_user.tenant_id,
        current_user.id,
        body.notification_ids,
        db,
    )
    return {"updated": updated}


@router.post(
    "/mark-all-read",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    summary="Mark all notifications as read",
)
async def mark_all_read(
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    updated = await service.mark_all_read(current_user.tenant_id, current_user.id, db)
    return {"updated": updated}


@router.post(
    "",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a manual notification (HR/Admin only)",
)
async def create_notification(
    body:         CreateNotificationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    _perm = require_permission("notifications", "write"),
):
    return await service.create_notification(
        tenant_id    = current_user.tenant_id,
        user_id      = body.user_id,
        title        = body.title,
        message      = body.message,
        db           = db,
        type         = body.type,
        category     = body.category,
        action_url   = body.action_url,
        action_label = body.action_label,
    )
