"""
AI-HRMS — Database Seeder
Creates the first super-admin user on initial startup if none exists.
"""

import structlog
from sqlalchemy import select, text

from app.core.config import settings
from app.core.database import AsyncSessionLocal

logger = structlog.get_logger(__name__)


async def seed_superadmin() -> None:
    """
    Creates the first super-admin user if no users exist in the database.
    Safe to call on every startup — idempotent.
    """
    async with AsyncSessionLocal() as session:
        try:
            # Check if users table exists first (before first migration)
            result = await session.execute(
                text(
                    "SELECT EXISTS ("
                    "  SELECT FROM information_schema.tables "
                    "  WHERE table_name = 'users'"
                    ")"
                )
            )
            table_exists = result.scalar()
            if not table_exists:
                logger.info("Users table not yet created — skipping seed")
                return

            # Check if any user exists
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()

            if user_count and user_count > 0:
                logger.debug("Users already exist — skipping superadmin seed")
                return

            # Import inside function to avoid circular imports
            from app.core.security import hash_password

            # 1. Create system tenant (idempotent via ON CONFLICT DO NOTHING)
            await session.execute(
                text(
                    """
                    INSERT INTO tenants (
                        id, name, slug, plan, is_active,
                        timezone, country, currency, created_at, updated_at
                    ) VALUES (
                        gen_random_uuid(), 'System', 'system',
                        'enterprise', true,
                        'Asia/Karachi', 'Pakistan', 'PKR', NOW(), NOW()
                    )
                    ON CONFLICT (slug) DO NOTHING
                    """
                )
            )
            await session.flush()

            # 2. Fetch the system tenant id
            tenant_result = await session.execute(
                text("SELECT id FROM tenants WHERE slug = 'system' LIMIT 1")
            )
            tenant_id = tenant_result.scalar()
            if not tenant_id:
                logger.error("Failed to create or retrieve system tenant")
                return

            # 3. Create super-admin user
            await session.execute(
                text(
                    """
                    INSERT INTO users (
                        id, tenant_id, email, hashed_password,
                        first_name, last_name,
                        is_active, is_verified, is_superadmin,
                        created_at, updated_at
                    ) VALUES (
                        gen_random_uuid(), :tenant_id, :email, :hashed_password,
                        :first_name, :last_name,
                        true, true, true, NOW(), NOW()
                    )
                    """
                ),
                {
                    "tenant_id": str(tenant_id),
                    "email": settings.FIRST_SUPERADMIN_EMAIL,
                    "hashed_password": hash_password(settings.FIRST_SUPERADMIN_PASSWORD),
                    "first_name": settings.FIRST_SUPERADMIN_FIRST_NAME,
                    "last_name": settings.FIRST_SUPERADMIN_LAST_NAME,
                },
            )
            await session.commit()

            logger.info(
                "Super-admin created",
                email=settings.FIRST_SUPERADMIN_EMAIL,
                tenant="system",
            )

            logger.info(
                "Super-admin created",
                email=settings.FIRST_SUPERADMIN_EMAIL,
            )

        except Exception as exc:
            await session.rollback()
            logger.warning("Seeder failed (non-fatal)", error=str(exc))
