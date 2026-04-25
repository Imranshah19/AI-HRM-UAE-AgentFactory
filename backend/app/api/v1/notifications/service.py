"""
AI-HRMS — Notifications service layer.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing   import Optional
from uuid     import UUID

from sqlalchemy           import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── Create ───────────────────────────────────────────────────────────────────

async def create_notification(
    tenant_id:    UUID,
    user_id:      UUID,
    title:        str,
    message:      str,
    db:           AsyncSession,
    type:         str          = "info",
    category:     str          = "general",
    action_url:   Optional[str]= None,
    action_label: Optional[str]= None,
) -> Notification:
    notif = Notification(
        tenant_id    = tenant_id,
        user_id      = user_id,
        title        = title,
        message      = message,
        type         = type,
        category     = category,
        action_url   = action_url,
        action_label = action_label,
        is_read      = False,
        channel      = "in_app",
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif


# ─── Read ─────────────────────────────────────────────────────────────────────

async def get_notifications(
    tenant_id: UUID,
    user_id:   UUID,
    db:        AsyncSession,
    limit:     int = 50,
) -> list[Notification]:
    rows = (await db.execute(
        select(Notification)
        .where(
            Notification.tenant_id == tenant_id,
            Notification.user_id   == user_id,
        )
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )).scalars().all()
    return list(rows)


async def get_unread_count(
    tenant_id: UUID,
    user_id:   UUID,
    db:        AsyncSession,
) -> int:
    count = (await db.execute(
        select(func.count(Notification.id)).where(
            Notification.tenant_id == tenant_id,
            Notification.user_id   == user_id,
            Notification.is_read   == False,
        )
    )).scalar_one()
    return count


# ─── Mark read ────────────────────────────────────────────────────────────────

async def mark_as_read(
    tenant_id:        UUID,
    user_id:          UUID,
    notification_ids: list[UUID],
    db:               AsyncSession,
) -> int:
    """Mark specific notifications as read. Returns number of rows updated."""
    result = await db.execute(
        update(Notification)
        .where(
            Notification.tenant_id == tenant_id,
            Notification.user_id   == user_id,
            Notification.id.in_(notification_ids),
            Notification.is_read   == False,
        )
        .values(is_read=True, read_at=_now())
    )
    await db.commit()
    return result.rowcount


async def mark_all_read(
    tenant_id: UUID,
    user_id:   UUID,
    db:        AsyncSession,
) -> int:
    result = await db.execute(
        update(Notification)
        .where(
            Notification.tenant_id == tenant_id,
            Notification.user_id   == user_id,
            Notification.is_read   == False,
        )
        .values(is_read=True, read_at=_now())
    )
    await db.commit()
    return result.rowcount


# ─── Cleanup ─────────────────────────────────────────────────────────────────

async def delete_old_notifications(db: AsyncSession) -> int:
    """Delete notifications older than 90 days. Run via Celery beat weekly."""
    cutoff = _now() - timedelta(days=90)
    result = await db.execute(
        delete(Notification).where(Notification.created_at < cutoff)
    )
    await db.commit()
    logger.info("Deleted %d old notifications", result.rowcount)
    return result.rowcount
