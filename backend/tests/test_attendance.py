"""
AI-HRMS — Attendance module tests.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from datetime  import date, datetime, time, timedelta
from httpx     import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AttendanceRecord, AttendanceAdjustment,
    Department, Employee, Shift, Tenant, User,
)
from app.core.security import get_password_hash


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_or_create_tenant(db: AsyncSession, slug: str = "att-test") -> Tenant:
    from sqlalchemy import select
    row = await db.execute(select(Tenant).where(Tenant.slug == slug))
    t   = row.scalar_one_or_none()
    if t:
        return t
    t = Tenant(name="Attendance Test Corp", slug=slug, is_active=True)
    db.add(t)
    await db.flush()
    return t


async def _create_user(
    db: AsyncSession, tenant_id: str, email: str = "att@test.com"
) -> User:
    u = User(
        tenant_id     = tenant_id,
        email         = email,
        password_hash = get_password_hash("Pass@1234"),
        first_name    = "Test",
        last_name     = "Attendance",
        is_active     = True,
        is_superadmin = False,
    )
    db.add(u)
    await db.flush()
    return u


async def _create_employee(
    db: AsyncSession, tenant_id: str, user_id: str,
    code: str = "ATT-001", shift_id: str | None = None,
) -> Employee:
    dept = Department(tenant_id=tenant_id, name="Attendance Dept", code="ATD")
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
        shift_id          = shift_id,
    )
    db.add(emp)
    await db.flush()
    return emp


async def _create_shift(
    db: AsyncSession, tenant_id: str,
    start: time = time(9, 0), end: time = time(17, 0), grace: int = 15,
) -> Shift:
    s = Shift(
        tenant_id            = tenant_id,
        name                 = "Standard",
        start_time           = start,
        end_time             = end,
        grace_period_minutes = grace,
        total_hours          = 8.0,
        is_active            = True,
    )
    db.add(s)
    await db.flush()
    return s


async def _make_superadmin(db: AsyncSession, user_id: str) -> None:
    await db.execute(
        text("UPDATE users SET is_superadmin = TRUE WHERE id = :uid"),
        {"uid": user_id},
    )
    await db.flush()


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def att_setup(test_db: AsyncSession):
    tenant = await _get_or_create_tenant(test_db)
    shift  = await _create_shift(test_db, str(tenant.id))
    user   = await _create_user(test_db, str(tenant.id))
    emp    = await _create_employee(test_db, str(tenant.id), str(user.id), shift_id=str(shift.id))
    await _make_superadmin(test_db, str(user.id))
    await test_db.commit()
    return tenant, user, emp, shift


# ─── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_in_success(
    test_client: AsyncClient, auth_headers: dict, att_setup, test_db: AsyncSession
):
    tenant, user, emp, shift = att_setup

    resp = await test_client.post(
        "/api/v1/attendance/check-in",
        json={"source": "manual"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["check_in"] is not None
    assert data["check_out"] is None
    assert data["status"] in ("present", "late")


@pytest.mark.asyncio
async def test_check_in_twice_same_day_fails(
    test_client: AsyncClient, auth_headers: dict, att_setup, test_db: AsyncSession
):
    tenant, user, emp, shift = att_setup

    # First check-in
    r1 = await test_client.post(
        "/api/v1/attendance/check-in",
        json={"source": "manual"},
        headers=auth_headers,
    )
    assert r1.status_code == 201

    # Second check-in same day
    r2 = await test_client.post(
        "/api/v1/attendance/check-in",
        json={"source": "manual"},
        headers=auth_headers,
    )
    assert r2.status_code == 409
    assert "already checked in" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_check_out_without_checkin_fails(
    test_client: AsyncClient, auth_headers: dict, att_setup, test_db: AsyncSession
):
    resp = await test_client.post(
        "/api/v1/attendance/check-out",
        json={},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "check in" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_late_arrival_marked_correctly(
    test_db: AsyncSession,
):
    """Service-level test: check-in after grace period marks status as late."""
    from app.api.v1.attendance.service import check_in
    from app.api.v1.attendance.schemas import AttendanceCheckInRequest, AttendanceStatus
    from unittest.mock import patch

    tenant = await _get_or_create_tenant(test_db, slug="att-late")
    shift  = await _create_shift(test_db, str(tenant.id), grace=0)  # zero grace = any lateness
    user   = await _create_user(test_db, str(tenant.id), "late@test.com")
    emp    = await _create_employee(test_db, str(tenant.id), str(user.id), code="ATT-L01", shift_id=str(shift.id))
    await test_db.commit()

    # Simulate check-in at 10:00 (well after 09:00 + 0 grace)
    late_time = datetime.combine(date.today(), time(10, 0, 0))

    with patch("app.api.v1.attendance.service.datetime") as mock_dt:
        mock_dt.utcnow.return_value = late_time
        mock_dt.combine = datetime.combine

        record = await check_in(
            str(tenant.id),
            str(emp.id),
            AttendanceCheckInRequest(source="manual"),
            test_db,
        )

    assert record.status == AttendanceStatus.late


@pytest.mark.asyncio
async def test_overtime_calculated_correctly(
    test_db: AsyncSession,
):
    """Check that check-out calculates overtime when working > 8 hours."""
    from app.api.v1.attendance.service import check_in, check_out
    from app.api.v1.attendance.schemas import (
        AttendanceCheckInRequest, AttendanceCheckOutRequest
    )
    from unittest.mock import patch

    tenant = await _get_or_create_tenant(test_db, slug="att-ot")
    shift  = await _create_shift(test_db, str(tenant.id))   # 8h shift
    user   = await _create_user(test_db, str(tenant.id), "ot@test.com")
    emp    = await _create_employee(test_db, str(tenant.id), str(user.id), code="ATT-OT1", shift_id=str(shift.id))
    await test_db.commit()

    check_in_time  = datetime.combine(date.today(), time(9, 0, 0))
    check_out_time = datetime.combine(date.today(), time(19, 0, 0))  # 10h total → 9h working (1h break)

    with patch("app.api.v1.attendance.service.datetime") as m:
        m.utcnow.return_value = check_in_time
        m.combine = datetime.combine
        await check_in(str(tenant.id), str(emp.id), AttendanceCheckInRequest(source="manual"), test_db)

    with patch("app.api.v1.attendance.service.datetime") as m:
        m.utcnow.return_value = check_out_time
        m.combine = datetime.combine
        record = await check_out(str(tenant.id), str(emp.id), AttendanceCheckOutRequest(), test_db)

    # 10h elapsed - 1h break = 9h working; 9h - 8h shift = 1h overtime
    assert record.working_hours  == pytest.approx(9.0, abs=0.1)
    assert record.overtime_hours == pytest.approx(1.0, abs=0.1)


@pytest.mark.asyncio
async def test_manual_entry_by_hr(
    test_client: AsyncClient, auth_headers: dict, att_setup, test_db: AsyncSession
):
    tenant, user, emp, shift = att_setup

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    check_in_dt  = f"{yesterday}T09:00:00"
    check_out_dt = f"{yesterday}T17:30:00"

    resp = await test_client.post(
        "/api/v1/attendance/records",
        json={
            "employee_id": str(emp.id),
            "date":       yesterday,
            "check_in":   check_in_dt,
            "check_out":  check_out_dt,
            "reason":     "System was down yesterday, adding manually",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["is_manual"] is True
    assert data["employee_id"] == str(emp.id)


@pytest.mark.asyncio
async def test_employee_cannot_manual_entry(
    test_client: AsyncClient, test_db: AsyncSession, att_setup
):
    """Plain employee (no attendance:manage permission) cannot create manual entries."""
    from app.core.security import create_access_token

    tenant, _, emp, _ = att_setup

    # Create a non-superadmin user
    plain_user = await _create_user(test_db, str(tenant.id), "plain@test.com")
    await _create_employee(test_db, str(tenant.id), str(plain_user.id), code="ATT-PL1")
    await test_db.commit()

    token   = create_access_token({"sub": str(plain_user.id), "tenant_id": str(tenant.id)})
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Slug": "att-test"}

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    resp = await test_client.post(
        "/api/v1/attendance/records",
        json={
            "employee_id": str(emp.id),
            "date":       yesterday,
            "check_in":   f"{yesterday}T09:00:00",
            "reason":     "Unauthorized manual entry attempt",
        },
        headers=headers,
    )
    assert resp.status_code in (403, 401)


@pytest.mark.asyncio
async def test_adjustment_request_and_approval(
    test_client: AsyncClient, auth_headers: dict, att_setup, test_db: AsyncSession
):
    tenant, user, emp, shift = att_setup

    # Create an attendance record to adjust
    rec = AttendanceRecord(
        tenant_id   = str(tenant.id),
        employee_id = str(emp.id),
        date        = date.today() - timedelta(days=2),
        check_in    = datetime.combine(date.today() - timedelta(days=2), time(9, 0)),
        status      = "present",
        source      = "manual",
        is_manual   = True,
    )
    test_db.add(rec)
    await test_db.commit()

    # Request adjustment
    req_resp = await test_client.post(
        "/api/v1/attendance/adjustments",
        json={
            "attendance_id": str(rec.id),
            "new_check_in":  f"{(date.today() - timedelta(days=2)).isoformat()}T08:45:00",
            "reason":        "Clock was slow that day, actual arrival was 8:45",
        },
        headers=auth_headers,
    )
    assert req_resp.status_code == 201, req_resp.text
    adj_id = req_resp.json()["id"]
    assert req_resp.json()["status"] == "pending"

    # Approve
    apr_resp = await test_client.post(
        f"/api/v1/attendance/adjustments/{adj_id}/approve",
        json={"action": "approve", "review_note": "Verified with badge log"},
        headers=auth_headers,
    )
    assert apr_resp.status_code == 200
    assert apr_resp.json()["status"] == "approved"

    # Verify record was updated
    await test_db.refresh(rec)
    assert rec.check_in.hour == 8
    assert rec.check_in.minute == 45


@pytest.mark.asyncio
async def test_monthly_summary_correct_counts(
    test_client: AsyncClient, auth_headers: dict, att_setup, test_db: AsyncSession
):
    tenant, user, emp, shift = att_setup

    today = date.today()
    month, year = today.month, today.year

    # Seed some records this month
    statuses = ["present", "present", "late", "absent", "on_leave"]
    for i, st in enumerate(statuses):
        d = date(year, month, max(1, today.day - (i + 1)))
        # Avoid weekend days
        while d.weekday() >= 5:
            d = d - timedelta(days=1)
        existing_row = await test_db.execute(
            __import__("sqlalchemy", fromlist=["select"]).select(AttendanceRecord).where(
                AttendanceRecord.employee_id == emp.id,
                AttendanceRecord.date        == d,
            )
        )
        if existing_row.scalar_one_or_none():
            continue
        test_db.add(AttendanceRecord(
            tenant_id   = str(tenant.id),
            employee_id = str(emp.id),
            date        = d,
            status      = st,
            source      = "manual",
            is_manual   = True,
            check_in    = datetime.combine(d, time(9, 0)) if st in ("present", "late") else None,
        ))
    await test_db.commit()

    resp = await test_client.get(
        f"/api/v1/attendance/summary/{emp.id}?month={month}&year={year}",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["employee_id"] == str(emp.id)
    assert data["month"]  == month
    assert data["year"]   == year
    assert data["total_working_days"] > 0
    assert "attendance_percentage" in data


@pytest.mark.asyncio
async def test_websocket_broadcasts_checkin_event(
    att_setup, test_db: AsyncSession
):
    """
    Verify that the WebSocket manager receives a broadcast on check-in.
    Uses mock to avoid actual WebSocket connections in tests.
    """
    from unittest.mock import AsyncMock, patch
    from app.api.v1.attendance.service import check_in
    from app.api.v1.attendance.schemas import AttendanceCheckInRequest

    tenant, user, emp, shift = att_setup

    broadcast_calls = []

    async def fake_broadcast(tenant_id, message):
        broadcast_calls.append((tenant_id, message))

    with patch("app.api.v1.attendance.service.manager") as mock_manager:
        mock_manager.broadcast_to_tenant = AsyncMock(side_effect=fake_broadcast)

        await check_in(
            str(tenant.id),
            str(emp.id),
            AttendanceCheckInRequest(source="mobile"),
            test_db,
        )

    # Should have been called once with check_in action
    assert len(broadcast_calls) == 1
    _tid, msg = broadcast_calls[0]
    assert _tid == str(tenant.id)
    assert msg["action"]    == "check_in"
    assert msg["type"]      == "attendance"
