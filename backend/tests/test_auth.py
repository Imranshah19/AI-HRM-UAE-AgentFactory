"""
AI-HRMS — Auth endpoint tests.

Coverage:
  POST /api/v1/auth/login
    - test_login_success
    - test_login_wrong_password
    - test_login_inactive_user

  GET  /api/v1/auth/me
    - test_me_authenticated
    - test_me_unauthenticated

  POST /api/v1/auth/refresh
    - test_refresh_token

  POST /api/v1/auth/logout
    - test_logout

  POST /api/v1/auth/change-password
    - test_change_password
"""

import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.tenant import Tenant, User

pytestmark = pytest.mark.asyncio


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _login_payload(email: str = "testadmin@test.local", password: str = "TestPass@123") -> dict:
    return {"email": email, "password": password}


# ─── Login ────────────────────────────────────────────────────────────────────

async def test_login_success(
    test_client: AsyncClient,
    test_user: User,
    test_tenant: Tenant,
):
    """Valid credentials return 200 with an access token and set cookies."""
    response = await test_client.post(
        "/api/v1/auth/login",
        json=_login_payload(),
        headers={"X-Tenant-Slug": test_tenant.slug},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0

    # httpOnly cookies must be set
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies


async def test_login_wrong_password(
    test_client: AsyncClient,
    test_user: User,
    test_tenant: Tenant,
):
    """Wrong password returns 401 and does not set auth cookies."""
    response = await test_client.post(
        "/api/v1/auth/login",
        json=_login_payload(password="WrongPassword!99"),
        headers={"X-Tenant-Slug": test_tenant.slug},
    )

    assert response.status_code == 401
    body = response.json()
    assert "Invalid email or password" in body["detail"]
    assert "access_token" not in response.cookies


async def test_login_inactive_user(
    test_client: AsyncClient,
    test_db: AsyncSession,
    test_user: User,
    test_tenant: Tenant,
):
    """Deactivated account returns 403 even with correct credentials."""
    # Deactivate the user
    test_user.is_active = False
    test_db.add(test_user)
    await test_db.flush()

    response = await test_client.post(
        "/api/v1/auth/login",
        json=_login_payload(),
        headers={"X-Tenant-Slug": test_tenant.slug},
    )

    assert response.status_code == 403
    body = response.json()
    assert "deactivated" in body["detail"].lower()

    # Restore for other tests (though each test rolls back, being explicit is safer)
    test_user.is_active = True
    test_db.add(test_user)
    await test_db.flush()


# ─── /me ──────────────────────────────────────────────────────────────────────

async def test_me_authenticated(
    test_client: AsyncClient,
    test_user: User,
    auth_headers: dict,
):
    """Authenticated request to /me returns the current user's profile."""
    response = await test_client.get("/api/v1/auth/me", headers=auth_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email"] == test_user.email
    assert body["first_name"] == test_user.first_name
    assert body["last_name"] == test_user.last_name
    assert str(body["id"]) == str(test_user.id)
    assert isinstance(body["roles"], list)
    assert isinstance(body["permissions"], list)


async def test_me_unauthenticated(test_client: AsyncClient):
    """Request without a token must be rejected with 401."""
    response = await test_client.get("/api/v1/auth/me")

    assert response.status_code == 401


# ─── Refresh Token ────────────────────────────────────────────────────────────

async def test_refresh_token(
    test_client: AsyncClient,
    test_user: User,
    test_tenant: Tenant,
):
    """
    Full flow: login → capture refresh token cookie → call /refresh →
    receive a new access token.
    """
    # Step 1: login to obtain cookies
    login_resp = await test_client.post(
        "/api/v1/auth/login",
        json=_login_payload(),
        headers={"X-Tenant-Slug": test_tenant.slug},
    )
    assert login_resp.status_code == 200, login_resp.text

    # Step 2: refresh using the cookie automatically forwarded by httpx
    refresh_resp = await test_client.post("/api/v1/auth/refresh")

    assert refresh_resp.status_code == 200, refresh_resp.text
    body = refresh_resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"

    # New access_token cookie must have been (re)set
    assert "access_token" in refresh_resp.cookies


# ─── Logout ───────────────────────────────────────────────────────────────────

async def test_logout(
    test_client: AsyncClient,
    test_user: User,
    test_tenant: Tenant,
):
    """
    After logout the refresh token is invalidated:
    a subsequent /refresh must return 401.
    """
    # 1. Login
    login_resp = await test_client.post(
        "/api/v1/auth/login",
        json=_login_payload(),
        headers={"X-Tenant-Slug": test_tenant.slug},
    )
    assert login_resp.status_code == 200

    # 2. Logout
    logout_resp = await test_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {login_resp.json()['access_token']}"},
    )
    assert logout_resp.status_code == 200
    body = logout_resp.json()
    assert "logged out" in body["message"].lower()

    # 3. Refresh after logout must fail
    refresh_resp = await test_client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == 401


# ─── Change Password ──────────────────────────────────────────────────────────

async def test_change_password(
    test_client: AsyncClient,
    test_db: AsyncSession,
    test_user: User,
    test_tenant: Tenant,
    auth_headers: dict,
):
    """
    Changing the password with correct old_password succeeds (200).
    The new password is persisted and the old password no longer works.
    """
    new_password = "NewSecure@456"

    response = await test_client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "TestPass@123", "new_password": new_password},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text

    # Reload user from DB and verify the hash changed
    await test_db.refresh(test_user)
    from app.core.security import verify_password
    assert verify_password(new_password, test_user.hashed_password)
    assert not verify_password("TestPass@123", test_user.hashed_password)

    # Restore original password so other fixtures still work within this session
    test_user.hashed_password = hash_password("TestPass@123")
    test_db.add(test_user)
    await test_db.flush()
