"""
AI-HRMS — Payroll module Celery tasks.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from typing   import List

from celery import shared_task

logger = logging.getLogger(__name__)


# ─── Process Payroll Run ──────────────────────────────────────────────────────

@shared_task(name="payroll.process_payroll_run", bind=True, max_retries=2)
def process_payroll_run(
    self,
    run_id:         str,
    tenant_id:      str,
    department_ids: List[str],
) -> dict:
    """
    Core payroll processing task.
    Fetches all active employees (optionally filtered by dept),
    calculates each employee's payroll, creates PayrollRecord rows,
    then updates PayrollRun totals and status → "processed".
    """

    async def _run() -> dict:
        from sqlalchemy import select, update as sql_update
        from sqlalchemy.orm import selectinload
        from app.core.database import AsyncSessionLocal
        from app.models import Employee, Department
        from app.models.payroll import PayrollRun, PayrollRecord
        from app.api.v1.payroll.service import (
            _fetch_payroll_inputs,
            get_tax_slabs,
        )
        from app.api.v1.payroll.calculator import (
            calculate_employee_payroll,
            TaxSlabData,
        )

        async with AsyncSessionLocal() as db:
            # Fetch the run
            run_row = await db.execute(
                select(PayrollRun).where(PayrollRun.id == run_id)
            )
            run = run_row.scalar_one_or_none()
            if not run:
                logger.error("PayrollRun %s not found", run_id)
                return {"error": "run_not_found", "run_id": run_id}

            # Fetch active employees
            emp_q = (
                select(Employee)
                .options(
                    selectinload(Employee.department),
                    selectinload(Employee.designation),
                )
                .where(
                    Employee.tenant_id        == tenant_id,
                    Employee.employment_status == "active",
                )
            )
            if department_ids:
                emp_q = emp_q.where(Employee.department_id.in_(department_ids))

            emp_rows = await db.execute(emp_q)
            employees = emp_rows.scalars().all()

            logger.info(
                "Processing payroll run %s: %d employees, month=%d/%d",
                run_id, len(employees), run.month, run.year,
            )

            # Fetch tax slabs once (shared across all employees for this year)
            tax_slabs_db = await get_tax_slabs(tenant_id, run.year, db)
            tax_slab_list = [
                TaxSlabData(
                    min_income = s.min_income,
                    max_income = s.max_income,
                    fixed_tax  = s.fixed_tax,
                    tax_rate   = float(s.tax_rate),
                )
                for s in tax_slabs_db
            ] if tax_slabs_db else None

            processed = 0
            total_gross      = 0
            total_net        = 0
            total_deductions = 0
            total_eobi_emp   = 0
            total_eobi_er    = 0
            total_tax        = 0

            for emp in employees:
                try:
                    _, salary_struct, att_summary, leave_summary, _ = await _fetch_payroll_inputs(
                        tenant_id, str(emp.id), run.month, run.year, db
                    )
                except Exception as exc:
                    logger.warning(
                        "Skipping employee %s (%s): %s",
                        emp.employee_code, emp.first_name, exc,
                    )
                    continue

                try:
                    result = calculate_employee_payroll(
                        employee_id = str(emp.id),
                        salary      = salary_struct,
                        attendance  = att_summary,
                        leaves      = leave_summary,
                        tax_slabs   = tax_slab_list,
                        month       = run.month,
                        year        = run.year,
                    )
                except Exception as exc:
                    logger.warning("Calculation failed for employee %s: %s", emp.id, exc)
                    continue

                record = PayrollRecord(
                    payroll_run_id         = run_id,
                    employee_id            = str(emp.id),
                    basic_salary           = result.basic_salary,
                    house_rent_allowance   = result.house_rent_allowance,
                    medical_allowance      = result.medical_allowance,
                    transport_allowance    = result.transport_allowance,
                    fuel_allowance         = result.fuel_allowance,
                    other_allowances       = result.other_allowances or None,
                    total_allowances       = result.total_allowances,
                    gross_salary           = result.gross_salary,
                    eobi_employee          = result.eobi_employee,
                    eobi_employer          = result.eobi_employer,
                    sessi                  = result.sessi,
                    income_tax             = result.income_tax,
                    loan_deduction         = result.loan_deduction,
                    advance_deduction      = result.advance_deduction,
                    other_deductions       = result.other_deductions or None,
                    total_deductions       = result.total_deductions,
                    net_salary             = result.net_salary,
                    working_days           = result.working_days,
                    present_days           = result.present_days,
                    absent_days            = result.absent_days,
                    late_days              = result.late_days,
                    overtime_hours         = result.overtime_hours or None,
                    paid_leave_days        = result.paid_leave_days,
                    unpaid_leave_days      = result.unpaid_leave_days,
                    is_prorated            = result.is_prorated,
                    status                 = "processed",
                )
                db.add(record)

                total_gross      += result.gross_salary
                total_net        += result.net_salary
                total_deductions += result.total_deductions
                total_eobi_emp   += result.eobi_employee
                total_eobi_er    += result.eobi_employer
                total_tax        += result.income_tax
                processed        += 1

            # Flush all records
            await db.flush()

            # Update run aggregates
            await db.execute(
                sql_update(PayrollRun)
                .where(PayrollRun.id == run_id)
                .values(
                    status            = "processed",
                    total_employees   = processed,
                    total_gross       = total_gross,
                    total_net         = total_net,
                    total_deductions  = total_deductions,
                    total_eobi_employee = total_eobi_emp,
                    total_eobi_employer = total_eobi_er,
                    total_income_tax  = total_tax,
                )
            )
            await db.commit()

            logger.info(
                "Payroll run %s complete: %d/%d employees processed.",
                run_id, processed, len(employees),
            )

            # Notify HR
            try:
                _notify_hr_payroll_complete(tenant_id, run_id, processed, total_net)
            except Exception:
                pass

            return {
                "run_id":    run_id,
                "processed": processed,
                "total":     len(employees),
                "total_net": total_net,
            }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.exception("process_payroll_run task failed: %s", exc)
        raise self.retry(exc=exc, countdown=60)


# ─── Generate All Payslips ─────────────────────────────────────────────────────

@shared_task(name="payroll.generate_all_payslips", bind=True, max_retries=1)
def generate_all_payslips(self, run_id: str, tenant_id: str) -> dict:
    """
    Generate PDF payslips for every record in a payroll run.
    Triggered after payroll run is approved.
    """

    async def _run() -> dict:
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.models.payroll import PayrollRecord, PayrollRun
        from app.api.v1.payroll.service import generate_payslip_pdf

        async with AsyncSessionLocal() as db:
            run_row = await db.execute(
                select(PayrollRun).where(PayrollRun.id == run_id)
            )
            run = run_row.scalar_one_or_none()
            if not run:
                return {"error": "run_not_found"}

            records_row = await db.execute(
                select(PayrollRecord).where(PayrollRecord.payroll_run_id == run_id)
            )
            records = records_row.scalars().all()

            generated = 0
            for record in records:
                try:
                    await generate_payslip_pdf(str(record.id), db)
                    generated += 1

                    # Queue email
                    send_payslip_email.delay(
                        str(record.employee_id),
                        record.payslip_url,
                        run.month,
                        run.year,
                    )
                except Exception as exc:
                    logger.warning("Failed to generate payslip for record %s: %s", record.id, exc)

            logger.info("Generated %d/%d payslips for run %s", generated, len(records), run_id)
            return {"run_id": run_id, "generated": generated, "total": len(records)}

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.exception("generate_all_payslips task failed: %s", exc)
        raise self.retry(exc=exc, countdown=30)


# ─── Send Payslip Email ───────────────────────────────────────────────────────

@shared_task(name="payroll.send_payslip_email", bind=True, max_retries=3)
def send_payslip_email(
    self,
    employee_id: str,
    payslip_url: str | None,
    month: int,
    year: int,
) -> None:
    """Send payslip email to an employee via SMTP."""

    async def _run() -> None:
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.models import Employee
        from app.core.config import settings

        async with AsyncSessionLocal() as db:
            emp_row = await db.execute(
                select(Employee).where(Employee.id == employee_id)
            )
            emp = emp_row.scalar_one_or_none()
            if not emp or not emp.work_email:
                logger.warning("Employee %s not found or has no email.", employee_id)
                return

            month_name = date(year, month, 1).strftime("%B %Y")
            subject    = f"Your {month_name} Salary Slip — AI-HRMS"
            body       = (
                f"Dear {emp.first_name},\n\n"
                f"Please find your salary slip for {month_name} attached.\n\n"
                f"Best regards,\nHR Department"
            )

            try:
                import smtplib
                from email.mime.text      import MIMEText
                from email.mime.multipart import MIMEMultipart

                msg           = MIMEMultipart()
                msg["From"]   = getattr(settings, "EMAIL_FROM", "hr@example.com")
                msg["To"]     = emp.work_email
                msg["Subject"] = subject
                msg.attach(MIMEText(body, "plain"))

                smtp_host = getattr(settings, "SMTP_HOST", "localhost")
                smtp_port = getattr(settings, "SMTP_PORT", 587)
                smtp_user = getattr(settings, "SMTP_USER", "")
                smtp_pass = getattr(settings, "SMTP_PASSWORD", "")

                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    if smtp_user:
                        server.login(smtp_user, smtp_pass)
                    server.sendmail(msg["From"], [msg["To"]], msg.as_string())

                logger.info("Payslip email sent to %s for %s", emp.work_email, month_name)

            except Exception as exc:
                logger.warning("Email send failed for %s: %s", emp.work_email, exc)
                raise

    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.exception("send_payslip_email task failed: %s", exc)
        raise self.retry(exc=exc, countdown=30)


# ─── Payroll Summary Report ───────────────────────────────────────────────────

@shared_task(name="payroll.generate_payroll_summary_report")
def generate_payroll_summary_report(tenant_id: str, run_id: str) -> dict:
    """
    Aggregate payroll statistics and return a summary dict.
    In production this would also email the Finance team.
    """

    async def _run() -> dict:
        from sqlalchemy import select, func
        from app.core.database import AsyncSessionLocal
        from app.models.payroll import PayrollRun, PayrollRecord
        from app.models import Employee, Department

        async with AsyncSessionLocal() as db:
            run_row = await db.execute(
                select(PayrollRun).where(PayrollRun.id == run_id)
            )
            run = run_row.scalar_one_or_none()
            if not run:
                return {"error": "run_not_found"}

            # Department-level breakdown
            dept_summary = await db.execute(
                select(
                    Department.name,
                    func.count(PayrollRecord.id).label("emp_count"),
                    func.sum(PayrollRecord.gross_salary).label("total_gross"),
                    func.sum(PayrollRecord.net_salary).label("total_net"),
                    func.sum(PayrollRecord.income_tax).label("total_tax"),
                )
                .join(Employee,    Employee.id   == PayrollRecord.employee_id)
                .join(Department,  Department.id == Employee.department_id)
                .where(PayrollRecord.payroll_run_id == run_id)
                .group_by(Department.name)
            )

            departments = []
            for row in dept_summary:
                departments.append({
                    "department":   row.name,
                    "employee_count": row.emp_count,
                    "total_gross":  int(row.total_gross or 0),
                    "total_net":    int(row.total_net or 0),
                    "total_tax":    int(row.total_tax or 0),
                })

            summary = {
                "run_id":          run_id,
                "month":           run.month,
                "year":            run.year,
                "total_employees": run.total_employees,
                "total_gross":     run.total_gross,
                "total_net":       run.total_net,
                "total_deductions": run.total_deductions,
                "total_income_tax": run.total_income_tax,
                "departments":     departments,
            }

            logger.info("Payroll summary report: run=%s employees=%d", run_id, run.total_employees)
            return summary

    return asyncio.run(_run())


# ─── Internal helper (not a Celery task) ──────────────────────────────────────

def _notify_hr_payroll_complete(
    tenant_id: str, run_id: str, processed: int, total_net: int
) -> None:
    """Create an in-app notification for HR that payroll processing is complete."""
    async def _notif():
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.models import User, Notification

        async with AsyncSessionLocal() as db:
            hr_users = await db.execute(
                select(User).where(
                    User.tenant_id    == tenant_id,
                    User.is_superadmin == True,
                )
            )
            for hr_user in hr_users.scalars().all():
                db.add(Notification(
                    tenant_id      = tenant_id,
                    user_id        = str(hr_user.id),
                    title          = "Payroll Processing Complete",
                    message        = (
                        f"Payroll has been processed for {processed} employees. "
                        f"Total net payable: PKR {total_net:,}."
                    ),
                    category       = "payroll",
                    reference_id   = run_id,
                    reference_type = "payroll_run",
                ))
            await db.commit()

    try:
        asyncio.run(_notif())
    except Exception as exc:
        logger.warning("HR payroll notification failed: %s", exc)
