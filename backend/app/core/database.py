"""
AI-HRMS — Async SQLAlchemy Database Engine & Session Factory
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, MappedColumn, mapped_column
from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.core.config import settings


# ─── Engine ───────────────────────────────────────────────────────────────────

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,              # Log SQL in development
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=True,               # Verify connections before use
)

# ─── Session Factory ──────────────────────────────────────────────────────────

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,           # Keep objects usable after commit
    autoflush=False,
    autocommit=False,
)


# ─── Base Model ───────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """
    Declarative base for all SQLAlchemy ORM models.
    All models should inherit from this class.
    """
    pass


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at columns to any model.
    """
    created_at: MappedColumn[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: MappedColumn[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """
    Mixin that uses UUID as the primary key instead of integer.
    """
    id: MappedColumn[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )


# ─── Dependency ───────────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session per request.

    Usage:
        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
