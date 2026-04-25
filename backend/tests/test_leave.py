"""
AI-HRMS — Leave Management tests.
Requires conftest.py fixtures: test_db, test_client, auth_headers.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from datetime   import date, timedelta
from httpx      import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Department, Designation, Employee, LeaveBalance,
    LeaveRequest, LeaveType, Tenant, User, UserRole,
)
from app.core.security import get_password_hash


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_or_create_tenant(db: AsyncSession, slug: str = "test") -> Tenant:
    from sqlalchemy import select
    row = await db.execute(select(Tenant).where(Tenant.slug == slug))
    t   = row.scalar_one_or_none()
    if t:
        return t
    t = Tenant(name="Test Corp", slug=slug, is_active=True)
    db.add(t)
    await db.flush()
    return t


async def _create_user(
    db: AsyncSession, tenant_id: str, email: str = "user@test.com"
) -> User:
    u = User(
        tenant_id      = tenant_id,
        email          = email,
        password_hash  = get_password_hash("Pass@1234"),
        first_name     = "Test",
        last_name      = "User",
        is_active      = True,
        is_superadmin  = False,
    )
    db.add(u)
    await db.flush()
    return u


async def _create_employee(
    db: AsyncSession, tenant_id: str, user_id: str, code: str = "EMP-0001"
) -> Employee:
    dept = Department(tenant_id=tenant_id, name="Engineering", code="ENG")
    db.add(dept)
    await db.flush()

    emp = Employee(
        tenant_id         = tenant_id,
        user_id           = user_id,
        employee_code     = code,
        first_name        = "Test",
        last_name         = "Employee",
        employment_status = "active",
        contract_type     = "permanent",
        department_id     = str(dept.id),
    )
    db.add(emp)
    await db.flush()
    return emp


async def _create_leave_type(
    db: AsyncSession, tenant_id: str, name: str = "Annual Leave", days: int = 20
) -> LeaveType:
    lt = LeaveType(
        tenant_id         = tenant_id,
        name              = name,
        days_allowed      = days,
        is_paid           = True,
        carry_forward     = False,
        max_carry_forward_days = 0,
        requires_document = False,
        color             = "#6366f1",
        is_active         = True,
    )
    db.add(lt)
    await db.flush()
    return lt


async def _create_balance(
    db: AsyncSession, tenant_id: str, employee_id: str,
    leave_type_id: str, total: int = 20, used: int = 0,
) -> LeaveBalance:
    bal = LeaveBalance(
        tenant_id      = tenant_id,
        employee_id    = employee_id,
        leave_type_id  = leave_type_id,
        year           = date.today().year,
        total_days     = total,
        used_days      = used,
        carried_forward= 0,
    )
    db.add(bal)
    await db.flush()
    return bal


async def _make_hr(db: AsyncSession, user_id: str, tenant_id: str) -> None:
    """Grant leave:approve + leave:manage to user via superadmin shortcut."""
    await db.execute(
        text("UPDATE users SET is_superadmin = TRUE WHERE id = :uid"),
        {"uid": user_id},
    )
    await db.flush()


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def leave_setup(test_db: AsyncSession):
    """Returns (client_factory, tenant, user, employee, leave_type, balance)."""
    tenant = await _get_or_create_tenant(test_db)
    user   = await _create_user(test_db, str(tenant.id))
    emp    = await _create_employee(test_db, str(tenant.id), str(user.id))
    lt     = await _create_leave_type(test_db, str(tenant.id))
    bal    = await _create_balance(test_db, str(tenant.id), str(emp.id), str(lt.id), total=20)
    await test_db.commit()
    return tenant, user, emp, lt, bal


# ─── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_leave_request_success(
    test_client: AsyncClient, auth_headers: dict, leave_setup, test_db: AsyncSession
):
    tenant, user, emp, lt, bal = leave_setup
    await _make_hr(test_db, str(user.id), str(tenant.id))
    await test_db.commit()

    start = (date.today() + timedelta(days=7)).isoformat()
    end   = (date.today() + timedelta(days=9)).isoformat()  # Mon-Wed ≈ 3 days

    resp = await test_client.post(
        "/api/v1/leave/requests",
        json={
            "leave_type_id": str(lt.id),
            "start_date":    start,
            "end_date":      end,
            "reason":        "Family vacation trip",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "pending"
    assert data["leave_type"]["id"] == str(lt.id)
    assert data["days"] >= 1  # at least 1 working day


@pytest.mark.asyncio
async def test_create_leave_request_insufficient_balance(
    test_client: AsyncClient, auth_headers: dict, leave_setup, test_db: AsyncSession
):
    tenant, user, emp, lt, bal = leave_setup
    await _make_hr(test_db, str(user.id), str(tenant.id))
    # Exhaust balance
    bal.used_days = 20
    await test_db.commit()

    resp = await test_client.post(
        "/api/v1/leave/requests",
        json={
            "leave_type_id": str(lt.id),
            "start_date":    (date.today() + timedelta(days=7)).isoformat(),
            "end_date":      (date.today() + timedelta(days=9)).isoformat(),
            "reason":        "Testing insufficient balance",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "Insufficient" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_create_leave_request_conflict(
    test_client: AsyncClient, auth_headers: dict, leave_setup, test_db: AsyncSession
):
    tenant, user, emp, lt, bal = leave_setup
    await _make_hr(test_db, str(user.id), str(tenant.id))
    await test_db.commit()

    start = (date.today() + timedelta(days=14)).isoformat()
    end   = (date.today() + timedelta(days=16)).isoformat()

    # First request
    r1 = await test_client.post(
        "/api/v1/leave/requests",
        json={"leave_type_id": str(lt.id), "start_date": start, "end_date": end,
              "reason": "First leave request test"},
        headers=auth_headers,
    )
    assert r1.status_code == 201

    # Conflicting request (same dates)
    r2 = await test_client.post(
        "/api/v1/leave/requests",
        json={"leave_type_id": str(lt.id), "start_date": start, "end_date": end,
              "reason": "Second conflicting leave"},
        headers=auth_headers,
    )
    assert r2.status_code == 409
    assert "conflict" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_approve_leave_request(
    test_client: AsyncClient, auth_headers: dict, leave_setup, test_db: AsyncSession
):
    tenant, user, emp, lt, bal = leave_setup
    await _make_hr(test_db, str(user.id), str(tenant.id))
    await test_db.commit()

    # Create request
    start = (date.today() + timedelta(days=21)).isoformat()
    end   = (date.today() + timedelta(days=22)).isoformat()
    cr = await test_client.post(
        "/api/v1/leave/requests",
        json={"leave_type_id": str(lt.id), "start_date": start, "end_date": end,
              "reason": "Approval test reason here"},
        headers=auth_headers,
    )
    assert cr.status_code == 201
    req_id = cr.json()["id"]

    # Approve
    ar = await test_client.post(
        f"/api/v1/leave/requests/{req_id}/approve",
        json={"action": "approve"},
        headers=auth_headers,
    )
    assert ar.status_code == 200
    assert ar.json()["status"] == "approved"

    # Balance should be deducted
    from sqlalchemy import select
    bal_row = await test_db.execute(
        select(LeaveBalance).where(
            LeaveBalance.employee_id  == emp.id,
            LeaveBalance.leave_type_id == lt.id,
        )
    )
    updated_bal = bal_row.scalar_one()
    assert updated_bal.used_days == cr.json()["days"]


@pytest.mark.asyncio
async def test_reject_leave_request_with_reason(
    test_client: AsyncClient, auth_headers: dict, leave_setup, test_db: AsyncSession
):
    tenant, user, emp, lt, bal = leave_setup
    await _make_hr(test_db, str(user.id), str(tenant.id))
    await test_db.commit()

    start = (date.today() + timedelta(days=28)).isoformat()
    end   = (date.today() + timedelta(days=29)).isoformat()
    cr = await test_client.post(
        "/api/v1/leave/requests",
        json={"leave_type_id": str(lt.id), "start_date": start, "end_date": end,
              "reason": "Testing rejection flow here"},
        headers=auth_headers,
    )
    assert cr.status_code == 201
    req_id = cr.json()["id"]

    # Reject without reason → 422
    bad = await test_client.post(
        f"/api/v1/leave/requests/{req_id}/approve",
        json={"action": "reject"},
        headers=auth_headers,
    )
    assert bad.status_code == 422

    # Reject with reason
    rr = await test_client.post(
        f"/api/v1/leave/requests/{req_id}/approve",
        json={"action": "reject", "rejection_reason": "Insufficient team coverage during this period."},
        headers=auth_headers,
    )
    assert rr.status_code == 200
    data = rr.json()
    assert data["status"] == "rejected"
    assert data["rejection_reason"] is not None


@pytest.mark.asyncio
async def test_cancel_approved_leave_restores_balance(
    test_client: AsyncClient, auth_headers: dict, leave_setup, test_db: AsyncSession
):
    tenant, user, emp, lt, bal = leave_setup
    await _make_hr(test_db, str(user.id), str(tenant.id))
    await test_db.commit()

    start = (date.today() + timedelta(days=35)).isoformat()
    end   = (date.today() + timedelta(days=37)).isoformat()

    cr = await test_client.post(
        "/api/v1/leave/requests",
        json={"leave_type_id": str(lt.id), "start_date": start, "end_date": end,
              "reason": "Cancel test after approval"},
        headers=auth_headers,
    )
    assert cr.status_code == 201
    req_id  = cr.json()["id"]
    req_days = cr.json()["days"]

    # Approve it
    await test_client.post(
        f"/api/v1/leave/requests/{req_id}/approve",
        json={"action": "approve"},
        headers=auth_headers,
    )

    # Check balance decreased
    from sqlalchemy import select
    bal_row = await test_db.execute(
        select(LeaveBalance).where(
            LeaveBalance.employee_id   == emp.id,
            LeaveBalance.leave_type_id == lt.id,
        )
    )
    mid_bal = bal_row.scalar_one()
    assert mid_bal.used_days == req_days

    # Cancel
    cancel_resp = await test_client.delete(
        f"/api/v1/leave/requests/{req_id}",
        headers=auth_headers,
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    # Balance should be restored
    await test_db.refresh(mid_bal)
    assert mid_bal.used_days == 0


@pytest.mark.asyncio
async def test_employee_cannot_see_others_leave(
    test_client: AsyncClient, test_db: AsyncSession
):
    from app.core.security import create_access_token

    tenant = await _get_or_create_tenant(test_db, slug="test-isolation")
    user1  = await _create_user(test_db, str(tenant.id), "emp1@test.com")
    user2  = await _create_user(test_db, str(tenant.id), "emp2@test.com")
    emp2   = await _create_employee(test_db, str(tenant.id), str(user2.id), code="EMP-0099")
    lt     = await _create_leave_type(test_db, str(tenant.id), name="Sick Leave")
    await _create_balance(test_db, str(tenant.id), str(emp2.id), str(lt.id))
    await test_db.commit()

    # Create a leave request for emp2
    req = LeaveRequest(
        tenant_id     = str(tenant.id),
        employee_id   = str(emp2.id),
        leave_type_id = str(lt.id),
        start_date    = date.today() + timedelta(days=5),
        end_date      = date.today() + timedelta(days=5),
        days          = 1,
        reason        = "Sick day for isolation test",
        status        = "pending",
    )
    test_db.add(req)
    await test_db.commit()

    # user1 (plain employee, no leave:approve permission) should NOT see emp2's request
    token   = create_access_token({"sub": str(user1.id), "tenant_id": str(tenant.id)})
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Slug": tenant.slug}

    resp = await test_client.get("/api/v1/leave/requests", headers=headers)
    assert resp.status_code == 200
    ids = [r["id"] for r in resp.json()["results"]]
    assert str(req.id) not in ids


@pytest.mark.asyncio
async def test_manager_can_see_team_leave(
    test_client: AsyncClient, test_db: AsyncSession
):
    from app.core.security import create_access_token

    tenant  = await _get_or_create_tenant(test_db, slug="test-manager")
    manager = await _create_user(test_db, str(tenant.id), "manager@test.com")
    emp_u   = await _create_user(test_db, str(tenant.id), "reportee@test.com")
    emp     = await _create_employee(test_db, str(tenant.id), str(emp_u.id), code="EMP-0101")
    lt      = await _create_leave_type(test_db, str(tenant.id), name="Annual")
    await _create_balance(test_db, str(tenant.id), str(emp.id), str(lt.id))
    # Make manager a superadmin (has leave:approve)
    await _make_hr(test_db, str(manager.id), str(tenant.id))
    await test_db.commit()

    # Create request for emp
    req = LeaveRequest(
        tenant_id     = str(tenant.id),
        employee_id   = str(emp.id),
        leave_type_id = str(lt.id),
        start_date    = date.today() + timedelta(days=5),
        end_date      = date.today() + timedelta(days=6),
        days          = 2,
        reason        = "Manager visibility test reason",
        status        = "pending",
    )
    test_db.add(req)
    await test_db.commit()

    token   = create_access_token({"sub": str(manager.id), "tenant_id": str(tenant.id)})
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Slug": tenant.slug}

    resp = await test_client.get("/api/v1/leave/requests", headers=headers)
    assert resp.status_code == 200
    ids = [r["id"] for r in resp.json()["results"]]
    assert str(req.id) in ids


@pytest.mark.asyncio
async def test_leave_calendar_returns_correct_month(
    test_client: AsyncClient, auth_headers: dict, leave_setup, test_db: AsyncSession
):
    tenant, user, emp, lt, bal = leave_setup
    await _make_hr(test_db, str(user.id), str(tenant.id))
    await test_db.commit()

    # Create an approved leave in the current month
    today = date.today()
    if today.day <= 25:
        leave_date = today.replace(day=today.day + 1)
    else:
        leave_date = today.replace(day=1)

    req = LeaveRequest(
        tenant_id     = str(tenant.id),
        employee_id   = str(emp.id),
        leave_type_id = str(lt.id),
        start_date    = leave_date,
        end_date      = leave_date,
        days          = 1,
        reason        = "Calendar test leave reason",
        status        = "approved",
    )
    test_db.add(req)
    await test_db.commit()

    resp = await test_client.get(
        f"/api/v1/leave/calendar?month={today.month}&year={today.year}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    entries = resp.json()

    # At least our approved leave should appear
    emp_ids = [e["employee_id"] for e in entries]
    assert str(emp.id) in emp_ids

    # All dates should fall in requested month/year
    for entry in entries:
        entry_date = date.fromisoformat(entry["date"])
        assert entry_date.month == today.month
        assert entry_date.year  == today.year
