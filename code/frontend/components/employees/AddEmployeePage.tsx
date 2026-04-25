"use client";

import React, { useState } from "react";
import AddEmployeeForm from "./AddEmployeeForm";
import EmployeeCreatedModal from "./EmployeeCreatedModal";
import { CreateEmployeeResponse } from "@/types/employee.types";

// ── Mock lookup data (replace with real API calls in production) ──────────────

const MOCK_DEPARTMENTS = [
  { id: "dept-001", name: "Engineering",       code: "ENG" },
  { id: "dept-002", name: "Human Resources",   code: "HR" },
  { id: "dept-003", name: "Finance",           code: "FIN" },
  { id: "dept-004", name: "Sales & Marketing", code: "SAL" },
  { id: "dept-005", name: "Operations",        code: "OPS" },
  { id: "dept-006", name: "IT Infrastructure", code: "IT" },
  { id: "dept-007", name: "Legal & Compliance",code: "LEG" },
];

const MOCK_BRANCHES = [
  { id: "br-001", name: "Head Office – Karachi",    city: "Karachi",   country: "Pakistan", timezone: "Asia/Karachi" },
  { id: "br-002", name: "Lahore Regional Office",   city: "Lahore",    country: "Pakistan", timezone: "Asia/Karachi" },
  { id: "br-003", name: "Islamabad Branch",          city: "Islamabad", country: "Pakistan", timezone: "Asia/Karachi" },
  { id: "br-004", name: "Dubai Office",              city: "Dubai",     country: "UAE",      timezone: "Asia/Dubai" },
];

const MOCK_MANAGERS = [
  { id: "emp-001", full_name: "Ahmed Khan",    designation: "VP Engineering",   department: "Engineering" },
  { id: "emp-002", full_name: "Sana Malik",    designation: "HR Director",      department: "Human Resources" },
  { id: "emp-003", full_name: "Raza Ahmed",    designation: "CFO",              department: "Finance" },
  { id: "emp-004", full_name: "Nadia Hussain", designation: "Head of Sales",    department: "Sales & Marketing" },
  { id: "emp-005", full_name: "Omar Sheikh",   designation: "IT Manager",       department: "IT Infrastructure" },
];

const MOCK_ROLES = [
  { id: "role-001", name: "Employee",          description: "Standard employee access",                    level: "employee"    as const },
  { id: "role-002", name: "Manager",           description: "Team management + approvals",                 level: "manager"     as const },
  { id: "role-003", name: "HR Manager",        description: "Full HR module access",                       level: "hr_manager"  as const },
  { id: "role-004", name: "Recruiter",         description: "ATS & recruitment access",                    level: "recruiter"   as const },
  { id: "role-005", name: "Finance Officer",   description: "Payroll & financial reports",                 level: "manager"     as const },
  { id: "role-006", name: "Super Admin",       description: "Full system access",                          level: "super_admin" as const },
];

const MOCK_SHIFTS = [
  { id: "sh-001", name: "Morning Shift",   start_time: "08:00", end_time: "17:00" },
  { id: "sh-002", name: "Afternoon Shift", start_time: "12:00", end_time: "21:00" },
  { id: "sh-003", name: "Night Shift",     start_time: "21:00", end_time: "06:00" },
  { id: "sh-004", name: "Flexible",        start_time: "09:00", end_time: "18:00" },
];

const MOCK_SALARY_STRUCTURES = [
  { id: "ss-001", name: "Standard Package",    description: "Basic + 40% HRA + 10% Medical" },
  { id: "ss-002", name: "Senior Package",      description: "Basic + 50% HRA + 15% Medical + Fuel" },
  { id: "ss-003", name: "Executive Package",   description: "Basic + 60% HRA + 20% Medical + Full Fuel + Utility" },
  { id: "ss-004", name: "Internship Package",  description: "Stipend only" },
];

// ─── Page Component ───────────────────────────────────────────────────────────

export default function AddEmployeePage() {
  const [successResult, setSuccessResult] = useState<CreateEmployeeResponse | null>(null);
  const [key, setKey] = useState(0); // reset form by re-mounting

  const handleSuccess = (result: CreateEmployeeResponse) => {
    setSuccessResult(result);
  };

  const handleViewProfile = () => {
    // Navigate to employee profile (integrate with your router)
    if (successResult) {
      window.location.href = `/employees/${successResult.employee_id}`;
    }
  };

  const handleAddAnother = () => {
    setSuccessResult(null);
    setKey((k) => k + 1);
    window.scrollTo({ top: 0 });
  };

  const handleCancel = () => {
    window.history.back();
  };

  return (
    <>
      <AddEmployeeForm
        key={key}
        departments={MOCK_DEPARTMENTS}
        branches={MOCK_BRANCHES}
        managers={MOCK_MANAGERS}
        employees={MOCK_MANAGERS}
        roles={MOCK_ROLES}
        shifts={MOCK_SHIFTS}
        salaryStructures={MOCK_SALARY_STRUCTURES}
        onSuccess={handleSuccess}
        onCancel={handleCancel}
      />

      {successResult && (
        <EmployeeCreatedModal
          result={successResult}
          onClose={handleViewProfile}
          onAddAnother={handleAddAnother}
        />
      )}
    </>
  );
}
