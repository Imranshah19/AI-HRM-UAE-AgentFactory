"""
Alembic Migration Environment — AI-HRMS

This file is invoked by Alembic CLI commands.
It reads the DATABASE_SYNC_URL from the app settings and sets up
both offline (SQL generation) and online (live DB) migration modes.
"""

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# ── Ensure the project root is on sys.path ────────────────────────────────────
# Allows `from app.core.config import settings` to work when running
# `alembic` from the /backend directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ── Load App Settings ─────────────────────────────────────────────────────────
from app.core.config import settings  # noqa: E402

# ── Import ALL models so Alembic can detect schema changes ────────────────────
# Importing app.models registers every table in Base.metadata automatically.
from app.models.base import Base  # noqa: E402 — all models inherit this Base
import app.models  # noqa: E402, F401 — registers all ORM models with Base.metadata

# ─── Alembic Config ───────────────────────────────────────────────────────────
config = context.config

# Load logging config from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override the sqlalchemy.url with our settings value
# We use the SYNC url here because Alembic uses synchronous connections
config.set_main_option("sqlalchemy.url", settings.DATABASE_SYNC_URL)

# The target metadata for autogenerate
target_metadata = Base.metadata


# ─── Offline Mode ─────────────────────────────────────────────────────────────
# Generates SQL scripts without a live DB connection.
# Usage: alembic upgrade head --sql

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Render column-level CHECK constraints
        render_as_batch=True,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ─── Online Mode (Sync) ────────────────────────────────────────────────────────
# Runs migrations against a live database connection.

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
        compare_type=True,
        compare_server_default=True,
        # Include schema name if using multi-schema setup
        # include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine (matches app's async engine)."""
    async_engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,  # Don't pool during migrations
    )
    async with async_engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await async_engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ─── Entry Point ──────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
