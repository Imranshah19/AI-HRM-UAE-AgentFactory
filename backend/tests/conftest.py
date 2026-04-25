"""
AI-HRMS — Pytest fixtures for the async test suite.

Fixture hierarchy:
  event_loop (session)
    └── test_engine (session)         — creates / drops test DB tables once
          └── test_db (function)      — per-test async session (rolls back)
                └── test_tenant       — a Tenant row
                └── test_user         — a User row with Admin role
                      └── auth_headers — {"Authorization": "Bearer <token>"}
  test_client (function)              — httpx.AsyncClient wired to the ASGI app
"""

import asyncio
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.redis import get_redis
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.tenant import Role, RolePermission, Tenant, User, UserRole, Permission

# ─── Test DB URL ──────────────────────────────────────────────────────────────
# Replace the main DB name with "<name>_test" so we never touch production data.
_TEST_DB_URL: str = settings.DATABASE_URL.replace(
    f"/{settings.POSTGRES_DB}",
    f"/{settings.POSTGRES_DB}_test",
    1,
)

# ─── Event Loop ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Single shared event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ─── Test Engine (session-scoped — tables created once) ───────────────────────

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """
    Create a dedicated test database engine.
    All SQLAlchemy tables are created before the first test and dropped after
    the last — keeping the test run self-contained.
    """
    engine = create_async_engine(
        _TEST_DB_URL,
        echo=False,
        pool_pre_ping=True,
    )

    # Ensure all model metadata is imported before create_all
    import app.models  # noqa: F401 — registers all ORM classes with Base

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# ─── Test DB Session (function-scoped — rolls back after every test) ──────────

@pytest_asyncio.fixture
async def test_db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Per-test async database session.

    Uses a nested transaction (SAVEPOINT) so that every test starts with a
    clean slate without truncating tables between tests.
    """
    TestSessionLocal = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    async with test_engine.connect() as conn:
        await conn.begin()
        async with TestSessionLocal(bind=conn) as session:
            await conn.begin_nested()  # SAVEPOINT

            yield session

            await session.rollback()
        await conn.rollback()


# ─── Override FastAPI dependencies ────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    httpx.AsyncClient wired to the FastAPI ASGI app.

    Both `get_db` and `get_redis` are overridden:
      - DB uses the rollback-safe test session.
      - Redis uses a real Redis connection on DB 15 (isolated test slot).
    """
    test_redis = Redis.from_url("redis://localhost:6379/15", decode_responses=True)

    async def _override_get_db():
        yield test_db

    async def _override_get_redis():
        return test_redis

    app.dependency_overrides[get_db]    = _override_get_db
    app.dependency_overrides[get_redis] = _override_get_redis

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Clean up test Redis keys and reset overrides
    await test_redis.flushdb()
    await test_redis.aclose()
    app.dependency_overrides.clear()


# ─── Test Tenant ──────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_tenant(test_db: AsyncSession) -> Tenant:
    """Create and persist a test Tenant row."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test Corp",
        slug=f"test-corp-{uuid.uuid4().hex[:8]}",
        plan="starter",
        is_active=True,
    )
    test_db.add(tenant)
    await test_db.flush()
    return tenant


# ─── Test User ────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_user(test_db: AsyncSession, test_tenant: Tenant) -> User:
    """
    Create a test User with an Admin role that has all permissions for the
    *employee_management* module.
    """
    # 1. Permission (if not already seeded)
    perm = Permission(
        id=uuid.uuid4(),
        module_name="employee_management",
        action="read",
        description="Read employees",
    )
    test_db.add(perm)
    await test_db.flush()

    # 2. Role
    role = Role(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        name="Admin",
        is_system_role=True,
    )
    test_db.add(role)
    await test_db.flush()

    # 3. Bind permission → role
    rp = RolePermission(role_id=role.id, permission_id=perm.id)
    test_db.add(rp)
    await test_db.flush()

    # 4. User
    user = User(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        email="testadmin@test.local",
        hashed_password=hash_password("TestPass@123"),
        first_name="Test",
        last_name="Admin",
        is_active=True,
        is_verified=True,
        is_superadmin=False,
    )
    test_db.add(user)
    await test_db.flush()

    # 5. Assign role → user
    ur = UserRole(user_id=user.id, role_id=role.id)
    test_db.add(ur)
    await test_db.flush()

    return user


# ─── Auth Headers ─────────────────────────────────────────────────────────────

@pytest.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    """Return an Authorization header containing a valid access token."""
    token = create_access_token(
        {
            "sub":       str(test_user.id),
            "tenant_id": str(test_user.tenant_id),
            "email":     test_user.email,
        }
    )
    return {"Authorization": f"Bearer {token}"}
