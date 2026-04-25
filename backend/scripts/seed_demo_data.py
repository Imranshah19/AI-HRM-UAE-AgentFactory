"""
AI-HRMS — Demo Data Seeder
Run from the backend directory:  python scripts/seed_demo_data.py

Creates a fully-populated demo tenant with realistic Pakistani employee data,
6 months of attendance, leave balances, 3 payroll runs, job postings/applications,
and a completed appraisal cycle.
"""

import asyncio
import os
import random
import sys
import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

# ── Allow `from app.*` imports when run directly ──────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://hrms_user:hrms_password@localhost:5432/hrms_db",
)

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

from app.core.security import hash_password
from app.models import (
    Tenant,
    User,
    Role,
    UserRole,
    Department,
    Designation,
    Employee,
    Shift,
    AttendanceRecord,
    LeaveType,
    LeaveBalance,
    PayrollRun,
    PayrollRecord,
    JobPosting,
    JobApplication,
    AppraisalCycle,
    Appraisal,
)

# ── Engine (reads DATABASE_URL from env) ──────────────────────────────────────
_db_url = os.environ["DATABASE_URL"]
engine = create_async_engine(_db_url, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# ── Constants ─────────────────────────────────────────────────────────────────

DEMO_TENANT_SLUG = "demo"
ADMIN_EMAIL = "demo@hrms.local"
ADMIN_PASSWORD = "Demo@1234!"

DEPARTMENTS = [
    {"name": "Engineering", "code": "ENG"},
    {"name": "HR", "code": "HR"},
    {"name": "Finance", "code": "FIN"},
    {"name": "Sales", "code": "SAL"},
    {"name": "Operations", "code": "OPS"},
]

# (title, dept_name, level, min_salary, max_salary)
DESIGNATIONS = [
    ("CTO",                "Engineering", "C-Level",  400000, 600000),
    ("Senior Engineer",    "Engineering", "Senior",   150000, 250000),
    ("Junior Engineer",    "Engineering", "Junior",    70000, 120000),
    ("HR Manager",         "HR",          "Manager",  120000, 180000),
    ("HR Officer",         "HR",          "Officer",   60000,  90000),
    ("CFO",                "Finance",     "C-Level",  350000, 550000),
    ("Accountant",         "Finance",     "Officer",   70000, 110000),
    ("Sales Manager",      "Sales",       "Manager",  130000, 200000),
    ("Sales Executive",    "Sales",       "Officer",   55000,  90000),
    ("Operations Manager", "Operations",  "Manager",  120000, 180000),
]

# Pakistani names (first, last, gender)
EMPLOYEES_DATA = [
    ("Ahmed",   "Hassan",    "male",   "Engineering", "Senior Engineer"),
    ("Muhammad","Ali",       "male",   "Engineering", "Junior Engineer"),
    ("Usman",   "Khan",      "male",   "Engineering", "Junior Engineer"),
    ("Bilal",   "Ahmed",     "male",   "Engineering", "Senior Engineer"),
    ("Farhan",  "Malik",     "male",   "Engineering", "CTO"),
    ("Zubair",  "Sheikh",    "male",   "HR",          "HR Manager"),
    ("Imran",   "Akhtar",    "male",   "Finance",     "CFO"),
    ("Kashif",  "Raza",      "male",   "Sales",       "Sales Manager"),
    ("Naveed",  "Hussain",   "male",   "Sales",       "Sales Executive"),
    ("Salman",  "Chaudhry",  "male",   "Operations",  "Operations Manager"),
    ("Ayesha",  "Siddiqi",   "female", "HR",          "HR Officer"),
    ("Fatima",  "Noor",      "female", "Finance",     "Accountant"),
    ("Sana",    "Malik",     "male",   "Sales",       "Sales Executive"),  # Sana can be male
    ("Hina",    "Khan",      "female", "HR",          "HR Officer"),
    ("Rabia",   "Iqbal",     "female", "Engineering", "Junior Engineer"),
    ("Zara",    "Ahmed",     "female", "Engineering", "Senior Engineer"),
    ("Maryam",  "Butt",      "female", "Finance",     "Accountant"),
    ("Nadia",   "Rehman",    "female", "Operations",  "Operations Manager"),
    ("Sara",    "Awan",      "female", "Sales",       "Sales Executive"),
    ("Amna",    "Mirza",     "female", "HR",          "HR Officer"),
]

LEAVE_TYPES = [
    {"name": "Annual Leave",  "code": "AL", "days": 15, "carry_forward": True,  "max_carry": 5,  "color": "#22c55e"},
    {"name": "Sick Leave",    "code": "SL", "days": 10, "carry_forward": False, "max_carry": 0,  "color": "#ef4444"},
    {"name": "Casual Leave",  "code": "CL", "days": 7,  "carry_forward": False, "max_carry": 0,  "color": "#3b82f6"},
]

JOB_POSTINGS = [
    {
        "title": "Python Backend Developer",
        "dept": "Engineering",
        "desig": "Senior Engineer",
        "status": "open",
        "vacancies": 2,
        "exp_min": 3,
        "exp_max": 6,
        "salary_min": 150000,
        "salary_max": 250000,
        "skills": ["Python", "FastAPI", "PostgreSQL", "Redis"],
        "description": "We are looking for an experienced Python backend developer to join our engineering team.",
        "requirements": "3+ years of Python experience. Proficiency in FastAPI or Django. PostgreSQL knowledge.",
    },
    {
        "title": "HR Business Partner",
        "dept": "HR",
        "desig": "HR Manager",
        "status": "open",
        "vacancies": 1,
        "exp_min": 4,
        "exp_max": 8,
        "salary_min": 120000,
        "salary_max": 180000,
        "skills": ["HR Management", "Recruitment", "Performance Management"],
        "description": "Seeking an experienced HR Business Partner to support our growing team.",
        "requirements": "Minimum 4 years of HR experience. MBA preferred.",
    },
    {
        "title": "Sales Executive – Karachi",
        "dept": "Sales",
        "desig": "Sales Executive",
        "status": "closed",
        "vacancies": 3,
        "exp_min": 1,
        "exp_max": 3,
        "salary_min": 55000,
        "salary_max": 90000,
        "skills": ["Sales", "CRM", "Negotiation"],
        "description": "Looking for dynamic sales executives to expand our Karachi market.",
        "requirements": "1-3 years of B2B sales experience. Strong communication skills.",
    },
    {
        "title": "Financial Analyst",
        "dept": "Finance",
        "desig": "Accountant",
        "status": "closed",
        "vacancies": 1,
        "exp_min": 2,
        "exp_max": 5,
        "salary_min": 80000,
        "salary_max": 130000,
        "skills": ["Financial Analysis", "Excel", "ERP", "ACCA"],
        "description": "Seeking a detail-oriented financial analyst to join our finance team.",
        "requirements": "ACCA/CA qualified or pursuing. 2+ years experience.",
    },
    {
        "title": "Operations Coordinator",
        "dept": "Operations",
        "desig": "Operations Manager",
        "status": "closed",
        "vacancies": 1,
        "exp_min": 2,
        "exp_max": 5,
        "salary_min": 70000,
        "salary_max": 110000,
        "skills": ["Operations Management", "Process Improvement", "Coordination"],
        "description": "Looking for an operations coordinator to streamline our daily processes.",
        "requirements": "2+ years in operations or supply chain. Strong organizational skills.",
    },
]

APPLICATIONS_DATA = [
    # (candidate_name, email, job_title_prefix, status, ai_score, source)
    ("Ali Raza",          "ali.raza@example.com",      "Python",    "shortlisted", 87.5,  "linkedin"),
    ("Waqas Mehmood",     "waqas.m@example.com",       "Python",    "interview",   91.2,  "portal"),
    ("Shahzad Baig",      "shahzad.b@example.com",     "Python",    "applied",     72.0,  "indeed"),
    ("Danish Yousaf",     "danish.y@example.com",      "Python",    "rejected",    45.3,  "portal"),
    ("Tariq Javed",       "tariq.j@example.com",       "Python",    "screening",   68.9,  "linkedin"),
    ("Sidra Rauf",        "sidra.r@example.com",       "HR",        "shortlisted", 83.1,  "linkedin"),
    ("Maham Aslam",       "maham.a@example.com",       "HR",        "interview",   78.4,  "portal"),
    ("Lubna Saeed",       "lubna.s@example.com",       "HR",        "applied",     61.0,  "direct"),
    ("Zeeshan Butt",      "zeeshan.b@example.com",     "Sales",     "hired",       88.0,  "referral"),
    ("Adnan Qureshi",     "adnan.q@example.com",       "Sales",     "hired",       84.5,  "portal"),
    ("Umer Farooq",       "umer.f@example.com",        "Sales",     "rejected",    39.2,  "indeed"),
    ("Kamran Shah",       "kamran.s@example.com",      "Financial", "hired",       90.3,  "linkedin"),
    ("Faizan Riaz",       "faizan.r@example.com",      "Financial", "rejected",    52.7,  "portal"),
    ("Asad Iqbal",        "asad.i@example.com",        "Operations","hired",       76.8,  "referral"),
    ("Hamza Latif",       "hamza.l@example.com",       "Operations","rejected",    44.1,  "portal"),
]


# ── Helper utilities ──────────────────────────────────────────────────────────

def _random_cnic() -> str:
    """Generate a plausible (fake) Pakistani CNIC."""
    return f"{random.randint(10000, 99999)}-{random.randint(1000000, 9999999)}-{random.randint(1, 9)}"


def _random_phone() -> str:
    prefixes = ["0300", "0301", "0302", "0303", "0311", "0312", "0321", "0333", "0345"]
    return f"{random.choice(prefixes)}{random.randint(1000000, 9999999)}"


def _employee_code(idx: int) -> str:
    return f"EMP-{idx:04d}"


def _work_email(first: str, last: str) -> str:
    return f"{first.lower()}.{last.lower()}@demo.hrms.local"


def _salary_for_designation(desig_name: str) -> int:
    for title, _, _, mn, mx in DESIGNATIONS:
        if title == desig_name:
            return random.randint(mn, mx)
    return 80000


def _join_date(idx: int) -> date:
    """Stagger join dates across 2023-2025."""
    base = date(2023, 1, 1)
    return base + timedelta(days=idx * 18)


# ── Seed functions ────────────────────────────────────────────────────────────

async def seed(session: AsyncSession) -> None:
    # ── 1. Idempotency check ──────────────────────────────────────────────────
    result = await session.execute(select(Tenant).where(Tenant.slug == DEMO_TENANT_SLUG))
    existing = result.scalar_one_or_none()
    if existing is not None:
        print("Demo tenant already exists — skipping seed.")
        return

    # ── 2. Tenant ─────────────────────────────────────────────────────────────
    print("Creating tenant...")
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Demo Company",
        slug=DEMO_TENANT_SLUG,
        plan="professional",
        is_active=True,
        timezone="Asia/Karachi",
        country="Pakistan",
        currency="PKR",
        settings={"modules": ["employee_management", "attendance", "payroll", "leave",
                               "performance", "recruitment"]},
    )
    session.add(tenant)
    await session.flush()

    # ── 3. Admin user ─────────────────────────────────────────────────────────
    print("Creating admin user...")
    admin_user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=ADMIN_EMAIL,
        hashed_password=hash_password(ADMIN_PASSWORD),
        first_name="Demo",
        last_name="Admin",
        is_active=True,
        is_verified=True,
        is_superadmin=False,
        timezone="Asia/Karachi",
    )
    session.add(admin_user)
    await session.flush()

    # ── 4. Admin role ─────────────────────────────────────────────────────────
    admin_role = Role(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Admin",
        description="Full administrative access",
        is_system_role=True,
    )
    session.add(admin_role)
    await session.flush()

    user_role_link = UserRole(
        user_id=admin_user.id,
        role_id=admin_role.id,
    )
    session.add(user_role_link)
    await session.flush()

    # ── 5. Departments ────────────────────────────────────────────────────────
    print("Creating departments...")
    dept_map: dict[str, Department] = {}
    for dept_info in DEPARTMENTS:
        dept = Department(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            name=dept_info["name"],
            code=dept_info["code"],
            is_active=True,
        )
        session.add(dept)
        dept_map[dept_info["name"]] = dept
    await session.flush()

    # ── 6. Designations ───────────────────────────────────────────────────────
    print("Creating designations...")
    desig_map: dict[str, Designation] = {}
    for title, dept_name, level, mn, mx in DESIGNATIONS:
        desig = Designation(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            name=title,
            department_id=dept_map[dept_name].id,
            level=level,
            min_salary=mn,
            max_salary=mx,
            is_active=True,
        )
        session.add(desig)
        desig_map[title] = desig
    await session.flush()

    # ── 7. Default shift ──────────────────────────────────────────────────────
    default_shift = Shift(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Standard 9-6",
        start_time=time(9, 0),
        end_time=time(18, 0),
        break_minutes=60,
        working_days=[0, 1, 2, 3, 4],  # Mon–Fri
        is_night_shift=False,
        late_threshold_minutes=15,
        half_day_hours=4.0,
        overtime_threshold_hours=8.0,
        is_active=True,
    )
    session.add(default_shift)
    await session.flush()

    # ── 8. Employees ──────────────────────────────────────────────────────────
    print("Creating 20 employees...")
    employees: list[Employee] = []
    for idx, (first, last, gender, dept_name, desig_name) in enumerate(EMPLOYEES_DATA, start=1):
        emp = Employee(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            employee_code=_employee_code(idx),
            first_name=first,
            last_name=last,
            gender=gender,
            work_email=_work_email(first, last),
            phone=_random_phone(),
            cnic=_random_cnic(),
            department_id=dept_map[dept_name].id,
            designation_id=desig_map[desig_name].id,
            shift_id=default_shift.id,
            contract_type="permanent",
            employment_status="active",
            work_schedule="full_time",
            join_date=_join_date(idx),
            nationality="Pakistani",
            dob=date(1988 + (idx % 12), (idx % 12) + 1, (idx % 28) + 1),
            marital_status="married" if idx % 3 == 0 else "single",
            timezone="Asia/Karachi",
            branch_location="Karachi",
            is_deleted=False,
        )
        session.add(emp)
        employees.append(emp)
    await session.flush()

    # Link manager relationships (first employee in each dept is the manager)
    dept_first_emp: dict[str, Employee] = {}
    for emp in employees:
        dept_id = str(emp.department_id)
        if dept_id not in dept_first_emp:
            dept_first_emp[dept_id] = emp

    for emp in employees:
        dept_id = str(emp.department_id)
        mgr = dept_first_emp.get(dept_id)
        if mgr and mgr.id != emp.id:
            emp.manager_id = mgr.id
    await session.flush()

    # ── 9. Leave types ────────────────────────────────────────────────────────
    print("Creating leave types...")
    leave_type_objs: list[LeaveType] = []
    for lt_info in LEAVE_TYPES:
        lt = LeaveType(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            name=lt_info["name"],
            code=lt_info["code"],
            days_allowed=lt_info["days"],
            carry_forward=lt_info["carry_forward"],
            max_carry_forward_days=lt_info["max_carry"],
            is_paid=True,
            applicable_gender="all",
            requires_document=False,
            allow_half_day=True,
            color=lt_info["color"],
            is_active=True,
        )
        session.add(lt)
        leave_type_objs.append(lt)
    await session.flush()

    # ── 10. Leave balances (2026) ─────────────────────────────────────────────
    print("Creating leave balances for 2026...")
    for emp in employees:
        for lt in leave_type_objs:
            used = round(random.uniform(0, lt.days_allowed * 0.4), 1)
            lb = LeaveBalance(
                id=uuid.uuid4(),
                employee_id=emp.id,
                leave_type_id=lt.id,
                year=2026,
                total_days=float(lt.days_allowed),
                used_days=used,
                pending_days=0.0,
                carried_days=float(lt.max_carry_forward_days) if lt.carry_forward else 0.0,
            )
            session.add(lb)
    await session.flush()

    # ── 11. Attendance history (Oct 2025 – Mar 2026) ──────────────────────────
    print("Creating 6 months attendance history (this may take a moment)...")
    attendance_start = date(2025, 10, 1)
    attendance_end = date(2026, 3, 31)

    current = attendance_start
    while current <= attendance_end:
        weekday = current.weekday()
        if weekday >= 5:  # Skip weekends
            current += timedelta(days=1)
            continue

        for emp in employees:
            roll = random.random()
            if roll < 0.05:
                status = "absent"
                check_in_dt = None
                check_out_dt = None
                working_hours = None
                late_minutes = None
            elif roll < 0.10:
                status = "on_leave"
                check_in_dt = None
                check_out_dt = None
                working_hours = None
                late_minutes = None
            elif roll < 0.18:
                # Late arrival
                status = "late"
                late_min = random.randint(16, 59)
                late_minutes = late_min
                ci_hour = 9
                ci_minute = late_min
                check_in_dt = datetime(current.year, current.month, current.day, ci_hour, ci_minute, tzinfo=timezone.utc)
                check_out_dt = datetime(current.year, current.month, current.day, 18, random.randint(0, 30), tzinfo=timezone.utc)
                working_hours = round((check_out_dt - check_in_dt).seconds / 3600, 2)
            else:
                status = "present"
                ci_minute = random.randint(0, 14)
                check_in_dt = datetime(current.year, current.month, current.day, 9, ci_minute, tzinfo=timezone.utc)
                co_minute = random.randint(0, 30)
                check_out_dt = datetime(current.year, current.month, current.day, 18, co_minute, tzinfo=timezone.utc)
                working_hours = round((check_out_dt - check_in_dt).seconds / 3600, 2)
                late_minutes = 0

            rec = AttendanceRecord(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                employee_id=emp.id,
                date=current,
                shift_id=default_shift.id,
                check_in=check_in_dt,
                check_in_source="web" if check_in_dt else None,
                check_out=check_out_dt,
                check_out_source="web" if check_out_dt else None,
                status=status,
                working_hours=working_hours,
                overtime_hours=max(0.0, round((working_hours or 0) - 8.0, 2)) if working_hours and working_hours > 8 else None,
                late_minutes=late_minutes,
                is_manual_entry=False,
            )
            session.add(rec)

        current += timedelta(days=1)

    await session.flush()

    # ── 12. Payroll runs (Jan, Feb, Mar 2026) ─────────────────────────────────
    print("Creating payroll runs (Jan-Mar 2026)...")
    payroll_months = [
        (1, 2026, "January 2026 Payroll",  "paid",     date(2026, 2, 1)),
        (2, 2026, "February 2026 Payroll", "paid",     date(2026, 3, 1)),
        (3, 2026, "March 2026 Payroll",    "approved", date(2026, 4, 1)),
    ]

    for month, year, label, pr_status, paid_dt in payroll_months:
        working_days_in_month = 22  # approximate

        total_gross = 0
        total_net = 0
        total_deductions = 0
        total_eobi_e = 0
        total_eobi_er = 0
        total_tax = 0

        run_id = uuid.uuid4()
        records_to_add = []

        for emp in employees:
            basic = _salary_for_designation(
                next(
                    (title for title, *_ in DESIGNATIONS
                     if desig_map[title].id == emp.designation_id),
                    "Junior Engineer",
                )
            )
            hra = int(basic * 0.40)
            medical = int(basic * 0.10)
            transport = int(basic * 0.05)
            total_allowances = hra + medical + transport
            gross = basic + total_allowances

            eobi_emp = min(int(basic * 0.01), 1600)   # 1% capped at PKR 1,600
            eobi_er = min(int(basic * 0.05), 8000)    # 5% employer capped at PKR 8,000
            annual_gross = gross * 12
            if annual_gross <= 600000:
                income_tax = 0
            elif annual_gross <= 1200000:
                income_tax = int((annual_gross - 600000) * 0.025 / 12)
            elif annual_gross <= 2400000:
                income_tax = int((15000 + (annual_gross - 1200000) * 0.125) / 12)
            else:
                income_tax = int((165000 + (annual_gross - 2400000) * 0.20) / 12)

            total_ded = eobi_emp + income_tax
            net = gross - total_ded

            present = random.randint(18, working_days_in_month)
            absent = working_days_in_month - present

            total_gross += gross
            total_net += net
            total_deductions += total_ded
            total_eobi_e += eobi_emp
            total_eobi_er += eobi_er
            total_tax += income_tax

            rec_status = "paid" if pr_status in ("paid",) else "processed"
            pr = PayrollRecord(
                id=uuid.uuid4(),
                payroll_run_id=run_id,
                employee_id=emp.id,
                basic_salary=basic,
                house_rent_allowance=hra,
                medical_allowance=medical,
                transport_allowance=transport,
                fuel_allowance=0,
                total_allowances=total_allowances,
                gross_salary=gross,
                eobi_employee=eobi_emp,
                eobi_employer=eobi_er,
                sessi=0,
                income_tax=income_tax,
                loan_deduction=0,
                advance_deduction=0,
                total_deductions=total_ded,
                net_salary=net,
                working_days=working_days_in_month,
                present_days=present,
                absent_days=absent,
                late_days=random.randint(0, 3),
                paid_leave_days=0.0,
                unpaid_leave_days=float(absent),
                is_prorated=False,
                status=rec_status,
            )
            records_to_add.append(pr)

        run_obj = PayrollRun(
            id=run_id,
            tenant_id=tenant.id,
            month=month,
            year=year,
            label=label,
            status=pr_status,
            total_employees=len(employees),
            total_gross=total_gross,
            total_net=total_net,
            total_deductions=total_deductions,
            total_eobi_employee=total_eobi_e,
            total_eobi_employer=total_eobi_er,
            total_income_tax=total_tax,
            processed_by=admin_user.id,
            approved_by=admin_user.id,
            run_at=datetime(year, month, 28, 10, 0, tzinfo=timezone.utc),
            approved_at=datetime(year, month, 28, 14, 0, tzinfo=timezone.utc),
            paid_at=datetime(paid_dt.year, paid_dt.month, paid_dt.day, 9, 0, tzinfo=timezone.utc) if pr_status == "paid" else None,
        )
        session.add(run_obj)
        for pr in records_to_add:
            session.add(pr)

    await session.flush()

    # ── 13. Job postings ──────────────────────────────────────────────────────
    print("Creating job postings...")
    posting_map: dict[str, JobPosting] = {}
    for jp_info in JOB_POSTINGS:
        dept_obj = dept_map.get(jp_info["dept"])
        desig_obj = desig_map.get(jp_info["desig"])
        posted_dt = datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc)
        closing = date(2026, 3, 31) if jp_info["status"] == "open" else date(2026, 2, 28)
        jp = JobPosting(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            title=jp_info["title"],
            department_id=dept_obj.id if dept_obj else None,
            designation_id=desig_obj.id if desig_obj else None,
            location="Karachi, Pakistan",
            description=jp_info["description"],
            requirements=jp_info["requirements"],
            vacancies=jp_info["vacancies"],
            employment_type="full_time",
            experience_years_min=jp_info["exp_min"],
            experience_years_max=jp_info["exp_max"],
            salary_min=jp_info["salary_min"],
            salary_max=jp_info["salary_max"],
            is_salary_visible=False,
            required_skills=jp_info["skills"],
            status=jp_info["status"],
            posted_by=admin_user.id,
            posted_at=posted_dt,
            closing_date=closing,
        )
        session.add(jp)
        posting_map[jp_info["title"]] = jp

    await session.flush()

    # ── 14. Job applications ──────────────────────────────────────────────────
    print("Creating 15 job applications...")
    for app_info in APPLICATIONS_DATA:
        candidate_name, email, title_prefix, app_status, ai_score, source = app_info

        # Match posting by title prefix
        matched_posting = None
        for title, jp_obj in posting_map.items():
            if title.startswith(title_prefix):
                matched_posting = jp_obj
                break
        if matched_posting is None:
            continue

        ai_scored_dt = datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc)
        applied_dt = datetime(2026, 1, 17, random.randint(9, 17), random.randint(0, 59), tzinfo=timezone.utc)

        app = JobApplication(
            id=uuid.uuid4(),
            job_posting_id=matched_posting.id,
            candidate_name=candidate_name,
            candidate_email=email,
            candidate_phone=_random_phone(),
            candidate_location="Karachi, Pakistan",
            source=source,
            applied_at=applied_dt,
            status=app_status,
            ai_score=ai_score,
            ai_explanation={
                "match_reasons": ["Relevant experience", "Skills match"],
                "gaps": ["Missing specific framework experience"] if ai_score < 70 else [],
                "skills_matched": matched_posting.required_skills[:2] if matched_posting.required_skills else [],
            },
            ai_scored_at=ai_scored_dt,
            is_archived=False,
            rejection_reason="Not enough experience" if app_status == "rejected" else None,
        )
        session.add(app)

    await session.flush()

    # ── 15. Appraisal cycle (Annual 2025) ─────────────────────────────────────
    print("Creating appraisal cycle (Annual 2025)...")
    cycle = AppraisalCycle(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Annual Performance Review 2025",
        year=2025,
        quarter=None,
        period_label="Annual 2025",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        self_review_deadline=date(2026, 1, 15),
        manager_review_deadline=date(2026, 1, 31),
        status="completed",
        rating_scale_min=1.0,
        rating_scale_max=5.0,
        self_review_instructions="Please complete your self-assessment honestly and comprehensively.",
        manager_review_instructions="Review employee performance against KPIs and provide constructive feedback.",
        created_by=admin_user.id,
    )
    session.add(cycle)
    await session.flush()

    # Appraisal records for all employees
    for emp in employees:
        self_rating = round(random.uniform(2.5, 5.0), 1)
        mgr_rating = round(random.uniform(2.5, 5.0), 1)
        final_rating = round((self_rating + mgr_rating) / 2, 1)
        attrition_risk = round(random.uniform(0.05, 0.45), 4)

        appraisal = Appraisal(
            id=uuid.uuid4(),
            cycle_id=cycle.id,
            employee_id=emp.id,
            reviewer_id=emp.manager_id,
            self_rating=self_rating,
            manager_rating=mgr_rating,
            final_rating=final_rating,
            kpi_scores=[
                {"kpi": "Work Quality",    "weight": 30, "self_score": self_rating, "mgr_score": mgr_rating},
                {"kpi": "Timeliness",      "weight": 25, "self_score": self_rating, "mgr_score": mgr_rating},
                {"kpi": "Teamwork",        "weight": 20, "self_score": self_rating, "mgr_score": mgr_rating},
                {"kpi": "Initiative",      "weight": 15, "self_score": self_rating, "mgr_score": mgr_rating},
                {"kpi": "Communication",   "weight": 10, "self_score": self_rating, "mgr_score": mgr_rating},
            ],
            self_strengths="Strong technical skills and team collaboration.",
            self_improvements="Wants to improve on time management and documentation.",
            self_achievements="Delivered key projects on time with high quality.",
            manager_feedback="Consistently meets expectations. Shows good initiative.",
            hr_comments="Solid performer. Consider for incremental raise.",
            predicted_rating=round(final_rating + random.uniform(-0.3, 0.3), 1),
            attrition_risk_score=attrition_risk,
            ai_insights={
                "flight_risk": "low" if attrition_risk < 0.2 else "medium" if attrition_risk < 0.35 else "high",
                "recommended_action": "Retain" if attrition_risk < 0.35 else "Monitor closely",
            },
            increment_recommended=final_rating >= 3.5,
            increment_percentage=round(random.uniform(5.0, 15.0), 2) if final_rating >= 3.5 else None,
            promotion_recommended=final_rating >= 4.5,
            status="completed",
            self_submitted_at=datetime(2026, 1, 12, 14, 0, tzinfo=timezone.utc),
            manager_submitted_at=datetime(2026, 1, 25, 11, 0, tzinfo=timezone.utc),
            finalized_at=datetime(2026, 2, 1, 10, 0, tzinfo=timezone.utc),
            employee_acknowledged=True,
            acknowledged_at=datetime(2026, 2, 3, 9, 0, tzinfo=timezone.utc),
        )
        session.add(appraisal)

    await session.flush()

    # ── Commit everything ─────────────────────────────────────────────────────
    await session.commit()
    print("\nDemo data seeded successfully!")
    print(f"  Tenant     : {tenant.name} (slug={tenant.slug})")
    print(f"  Admin login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"  Employees  : {len(employees)}")
    print(f"  Leave types: {len(leave_type_objs)}")
    print(f"  Payroll runs: 3 (Jan-Mar 2026)")
    print(f"  Job postings: {len(JOB_POSTINGS)} (2 open, 3 closed)")
    print(f"  Applications: {len(APPLICATIONS_DATA)}")
    print(f"  Appraisal cycle: Annual 2025 (completed)")


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
