"""
AI-HRMS — Employee API tests.

Coverage:
  POST   /api/v1/employees              — create employee
  GET    /api/v1/employees              — list with pagination / filters
  GET    /api/v1/employees/{id}         — detail
  PATCH  /api/v1/employees/{id}         — update
  PATCH  /api/v1/employees/{id}/status  — status transition
  POST   /api/v1/employees/{id}/documents — document upload
  GET    /api/v1/employees/export       — Excel export
"""

import io
import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.employee import Department, Designation, Employee
from app.models.tenant import Permission, Role, RolePermission, Tenant, User, UserRole

pytestmark = pytest.mark.asyncio


# ─── Extra fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def admin_headers(test_user: User) -> dict[str, str]:
    """Superadmin token — bypasses all permission checks."""
    from app.core.security import create_access_token
    token = create_access_token(
        {
            "sub":       str(test_user.id),
            "tenant_id": str(test_user.tenant_id),
            "email":     test_user.email,
        }
    )
    return {"Authorization": f"Bearer {token}"}


async def _make_superadmin(user: User, db: AsyncSession) -> None:
    """Promote a user to superadmin so all permission checks pass."""
    user.is_superadmin = True
    db.add(user)
    await db.flush()


async def _create_department(tenant_id: uuid.UUID, db: AsyncSession, name: str = "Engineering") -> Department:
    dept = Department(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=name,
        is_active=True,
    )
    db.add(dept)
    await db.flush()
    return dept


async def _create_designation(
    tenant_id: uuid.UUID,
    db: AsyncSession,
    department: Department,
    name: str = "Software Engineer",
) -> Designation:
    desig = Designation(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=name,
        department_id=department.id,
        is_active=True,
    )
    db.add(desig)
    await db.flush()
    return desig


def _employee_payload(
    department_id: uuid.UUID | None = None,
    designation_id: uuid.UUID | None = None,
    cnic: str = "42101-1234567-1",
    first_name: str = "Alice",
    last_name: str = "Smith",
) -> dict:
    return {
        "first_name":   first_name,
        "last_name":    last_name,
        "cnic":         cnic,
        "phone":        "+923001234567",
        "gender":       "female",
        "dob":          "1992-05-15",
        "nationality":  "Pakistani",
        "department_id":   str(department_id) if department_id else None,
        "designation_id":  str(designation_id) if designation_id else None,
        "contract_type":   "permanent",
        "join_date":       "2024-01-15",
        "basic_salary":    80000,
        "house_rent_allowance": 20000,
        "medical_allowance":    5000,
        "transport_allowance":  3000,
        "bank_name":      "HBL",
        "account_title":  f"{first_name} {last_name}",
        "account_number": "01234567890123",
        "iban":           "PK36SCBL0000001123456702",
        "eobi_applicable": True,
        "income_tax_applicable": True,
    }


# ─── test_create_employee_success ─────────────────────────────────────────────

async def test_create_employee_success(
    test_client: AsyncClient,
    test_db:     AsyncSession,
    test_tenant: Tenant,
    test_user:   User,
    admin_headers: dict,
):
    await _make_superadmin(test_user, test_db)

    dept  = await _create_department(test_tenant.id, test_db)
    desig = await _create_designation(test_tenant.id, test_db, dept)

    response = await test_client.post(
        "/api/v1/employees",
        json=_employee_payload(department_id=dept.id, designation_id=desig.id),
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["employee_code"].startswith("EMP-")
    assert body["work_email"].endswith(".ai-hrms.com")
    assert body["full_name"] == "Alice Smith"


# ─── test_create_employee_duplicate_cnic ──────────────────────────────────────

async def test_create_employee_duplicate_cnic(
    test_client:   AsyncClient,
    test_db:       AsyncSession,
    test_tenant:   Tenant,
    test_user:     User,
    admin_headers: dict,
):
    await _make_superadmin(test_user, test_db)

    cnic = "35201-9876543-2"
    payload = _employee_payload(cnic=cnic)

    # First creation succeeds
    r1 = await test_client.post(
        "/api/v1/employees",
        json=payload,
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )
    assert r1.status_code == 201, r1.text

    # Second creation with same CNIC must fail with 409
    payload2 = _employee_payload(
        cnic=cnic,
        first_name="Bob",
        last_name="Jones",
    )
    r2 = await test_client.post(
        "/api/v1/employees",
        json=payload2,
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )
    assert r2.status_code == 409
    assert "CNIC" in r2.json()["detail"]


# ─── test_list_employees_pagination ───────────────────────────────────────────

async def test_list_employees_pagination(
    test_client:   AsyncClient,
    test_db:       AsyncSession,
    test_tenant:   Tenant,
    test_user:     User,
    admin_headers: dict,
):
    await _make_superadmin(test_user, test_db)

    # Seed 3 employees
    for i in range(3):
        await test_client.post(
            "/api/v1/employees",
            json=_employee_payload(
                cnic=f"4210{i}-1234567-{i}",
                first_name=f"Emp{i}",
                last_name="Doe",
            ),
            headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
        )

    # Page 1, size 2
    r = await test_client.get(
        "/api/v1/employees?page=1&page_size=2",
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    assert body["total"] >= 3
    assert body["pages"] >= 2

    # Page 2
    r2 = await test_client.get(
        "/api/v1/employees?page=2&page_size=2",
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )
    assert r2.status_code == 200
    assert len(r2.json()["items"]) >= 1


# ─── test_list_employees_filter_by_department ─────────────────────────────────

async def test_list_employees_filter_by_department(
    test_client:   AsyncClient,
    test_db:       AsyncSession,
    test_tenant:   Tenant,
    test_user:     User,
    admin_headers: dict,
):
    await _make_superadmin(test_user, test_db)

    dept_a = await _create_department(test_tenant.id, test_db, "Sales")
    dept_b = await _create_department(test_tenant.id, test_db, "Finance")

    # One employee in Sales, one in Finance
    await test_client.post(
        "/api/v1/employees",
        json=_employee_payload(department_id=dept_a.id, cnic="11111-1111111-1", first_name="Sales", last_name="Person"),
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )
    await test_client.post(
        "/api/v1/employees",
        json=_employee_payload(department_id=dept_b.id, cnic="22222-2222222-2", first_name="Finance", last_name="Person"),
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )

    # Filter by Sales department
    r = await test_client.get(
        f"/api/v1/employees?department_id={dept_a.id}",
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert all(
        item["department"]["id"] == str(dept_a.id)
        for item in items
        if item.get("department")
    )


# ─── test_list_employees_search ───────────────────────────────────────────────

async def test_list_employees_search(
    test_client:   AsyncClient,
    test_db:       AsyncSession,
    test_tenant:   Tenant,
    test_user:     User,
    admin_headers: dict,
):
    await _make_superadmin(test_user, test_db)

    await test_client.post(
        "/api/v1/employees",
        json=_employee_payload(cnic="55555-5555555-5", first_name="Zubair", last_name="Khan"),
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )
    await test_client.post(
        "/api/v1/employees",
        json=_employee_payload(cnic="66666-6666666-6", first_name="Sana", last_name="Ali"),
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )

    r = await test_client.get(
        "/api/v1/employees?search=Zubair",
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )
    assert r.status_code == 200
    items = r.json()["items"]
    # All results should contain "Zubair" in their name
    assert all("Zubair" in item["full_name"] for item in items)


# ─── test_get_employee_detail ─────────────────────────────────────────────────

async def test_get_employee_detail(
    test_client:   AsyncClient,
    test_db:       AsyncSession,
    test_tenant:   Tenant,
    test_user:     User,
    admin_headers: dict,
):
    await _make_superadmin(test_user, test_db)

    create_resp = await test_client.post(
        "/api/v1/employees",
        json=_employee_payload(cnic="77777-7777777-7", first_name="Detail", last_name="Test"),
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )
    assert create_resp.status_code == 201
    employee_id = create_resp.json()["id"]

    r = await test_client.get(
        f"/api/v1/employees/{employee_id}",
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == employee_id
    assert body["first_name"] == "Detail"
    assert body["last_name"] == "Test"
    assert body["employment_status"] == "active"
    # Salary should be present (we submitted basic_salary=80000)
    assert body["salary"] is not None
    assert body["salary"]["basic_salary"] == 80000
    # Bank details should be present
    assert len(body["bank_details"]) == 1
    assert body["bank_details"][0]["bank_name"] == "HBL"


# ─── test_get_employee_wrong_tenant ───────────────────────────────────────────

async def test_get_employee_wrong_tenant(
    test_client:   AsyncClient,
    test_db:       AsyncSession,
    test_tenant:   Tenant,
    test_user:     User,
    admin_headers: dict,
):
    """Requesting an employee that belongs to a different tenant must return 404."""
    await _make_superadmin(test_user, test_db)

    # Create a second tenant + employee
    from app.models.tenant import Tenant as TenantModel
    other_tenant = TenantModel(
        id=uuid.uuid4(),
        name="Other Corp",
        slug=f"other-corp-{uuid.uuid4().hex[:8]}",
        plan="starter",
        is_active=True,
    )
    test_db.add(other_tenant)
    await test_db.flush()

    other_employee = Employee(
        id=uuid.uuid4(),
        tenant_id=other_tenant.id,
        employee_code="EMP-9999",
        first_name="Foreign",
        last_name="Employee",
        contract_type="permanent",
        employment_status="active",
        is_deleted=False,
    )
    test_db.add(other_employee)
    await test_db.flush()

    # Our test_tenant's user tries to access the other tenant's employee
    r = await test_client.get(
        f"/api/v1/employees/{other_employee.id}",
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )
    assert r.status_code == 404


# ─── test_update_employee ─────────────────────────────────────────────────────

async def test_update_employee(
    test_client:   AsyncClient,
    test_db:       AsyncSession,
    test_tenant:   Tenant,
    test_user:     User,
    admin_headers: dict,
):
    await _make_superadmin(test_user, test_db)

    create_resp = await test_client.post(
        "/api/v1/employees",
        json=_employee_payload(cnic="88888-8888888-8", first_name="Update", last_name="Me"),
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )
    employee_id = create_resp.json()["id"]

    patch_resp = await test_client.patch(
        f"/api/v1/employees/{employee_id}",
        json={
            "first_name":    "Updated",
            "branch_location": "Lahore Office",
            "nationality":   "British",
        },
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )
    assert patch_resp.status_code == 200
    body = patch_resp.json()
    assert body["first_name"]      == "Updated"
    assert body["branch_location"] == "Lahore Office"
    assert body["nationality"]     == "British"


# ─── test_update_employee_status_terminated ───────────────────────────────────

async def test_update_employee_status_terminated(
    test_client:   AsyncClient,
    test_db:       AsyncSession,
    test_tenant:   Tenant,
    test_user:     User,
    admin_headers: dict,
):
    await _make_superadmin(test_user, test_db)

    create_resp = await test_client.post(
        "/api/v1/employees",
        json=_employee_payload(cnic="99999-9999999-9", first_name="Terminate", last_name="Me"),
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )
    employee_id = create_resp.json()["id"]

    status_resp = await test_client.patch(
        f"/api/v1/employees/{employee_id}/status",
        json={
            "employment_status": "terminated",
            "reason":           "End of contract",
            "effective_date":   str(date.today()),
        },
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )
    assert status_resp.status_code == 200
    body = status_resp.json()
    assert body["employment_status"]  == "terminated"
    assert body["termination_reason"] == "End of contract"
    assert body["termination_date"]   is not None


# ─── test_upload_document ─────────────────────────────────────────────────────

async def test_upload_document(
    test_client:   AsyncClient,
    test_db:       AsyncSession,
    test_tenant:   Tenant,
    test_user:     User,
    admin_headers: dict,
    tmp_path,
):
    await _make_superadmin(test_user, test_db)

    # Create employee
    create_resp = await test_client.post(
        "/api/v1/employees",
        json=_employee_payload(cnic="33333-3333333-3", first_name="Doc", last_name="Upload"),
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )
    employee_id = create_resp.json()["id"]

    # Create a minimal valid PDF (enough bytes to pass mime check)
    fake_pdf = b"%PDF-1.4 fake content for testing"

    r = await test_client.post(
        f"/api/v1/employees/{employee_id}/documents",
        files={"file": ("cnic_front.pdf", io.BytesIO(fake_pdf), "application/pdf")},
        data={"doc_type": "cnic_front"},
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["doc_type"] == "cnic_front"
    assert body["is_verified"] is False


# ─── test_upload_document_too_large ───────────────────────────────────────────

async def test_upload_document_too_large(
    test_client:   AsyncClient,
    test_db:       AsyncSession,
    test_tenant:   Tenant,
    test_user:     User,
    admin_headers: dict,
):
    await _make_superadmin(test_user, test_db)

    create_resp = await test_client.post(
        "/api/v1/employees",
        json=_employee_payload(cnic="44444-4444444-4", first_name="BigFile", last_name="Test"),
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )
    employee_id = create_resp.json()["id"]

    # Generate a file slightly larger than 5 MB
    oversized = b"x" * (5 * 1024 * 1024 + 1)

    r = await test_client.post(
        f"/api/v1/employees/{employee_id}/documents",
        files={"file": ("big.pdf", io.BytesIO(oversized), "application/pdf")},
        data={"doc_type": "cv_resume"},
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )
    assert r.status_code == 413


# ─── test_export_employees_excel ──────────────────────────────────────────────

async def test_export_employees_excel(
    test_client:   AsyncClient,
    test_db:       AsyncSession,
    test_tenant:   Tenant,
    test_user:     User,
    admin_headers: dict,
):
    await _make_superadmin(test_user, test_db)

    # Seed one employee
    await test_client.post(
        "/api/v1/employees",
        json=_employee_payload(cnic="11100-1110000-1", first_name="Export", last_name="Test"),
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )

    r = await test_client.get(
        "/api/v1/employees/export",
        headers={**admin_headers, "X-Tenant-Slug": test_tenant.slug},
    )

    # Either succeeds (openpyxl installed) or 501 (not installed in test env)
    assert r.status_code in (200, 501)

    if r.status_code == 200:
        assert (
            r.headers["content-type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert len(r.content) > 0
        # Verify it's a valid ZIP (xlsx is a ZIP)
        assert r.content[:4] == b"PK\x03\x04"
