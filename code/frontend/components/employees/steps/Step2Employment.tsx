"use client";

import React from "react";
import { UseFormReturn } from "react-hook-form";
import { AddEmployeeFormData } from "@/schemas/employee.schema";
import { Department, Branch, Employee, Shift } from "@/types/employee.types";

interface Props {
  form: UseFormReturn<AddEmployeeFormData>;
  departments: Department[];
  branches: Branch[];
  managers: Employee[];
  shifts: Shift[];
}

const TIMEZONES = [
  "Asia/Karachi",
  "Asia/Kolkata",
  "Asia/Dubai",
  "Asia/Riyadh",
  "Europe/London",
  "America/New_York",
  "America/Los_Angeles",
  "Australia/Sydney",
];

export default function Step2Employment({
  form,
  departments,
  branches,
  managers,
  shifts,
}: Props) {
  const { register, formState: { errors }, watch } = form;
  const contractType = watch("contract_type");
  const workSchedule = watch("work_schedule");

  return (
    <div className="space-y-8">
      {/* ── Employment Identity ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Employment Identity
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField label="Employee ID" required error={errors.employee_id?.message}>
            <input
              {...register("employee_id")}
              type="text"
              placeholder="EMP-2026-001"
              className={inputClass(errors.employee_id)}
            />
          </FormField>

          <FormField label="Work Email" required error={errors.work_email?.message}>
            <input
              {...register("work_email")}
              type="email"
              placeholder="name@company.com"
              className={inputClass(errors.work_email)}
            />
          </FormField>

          <FormField label="Designation / Job Title" required error={errors.designation?.message}>
            <input
              {...register("designation")}
              type="text"
              placeholder="Senior Software Engineer"
              className={inputClass(errors.designation)}
            />
          </FormField>

          <FormField label="Grade Level" error={errors.grade_level?.message}>
            <input
              {...register("grade_level")}
              type="text"
              placeholder="L3 / M1 / Senior"
              className={inputClass(errors.grade_level)}
            />
          </FormField>
        </div>
      </div>

      {/* ── Department & Location ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Department & Location
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField label="Department" required error={errors.department_id?.message}>
            <select {...register("department_id")} className={inputClass(errors.department_id)}>
              <option value="">Select department</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </FormField>

          <FormField label="Branch / Office Location" required error={errors.branch_id?.message}>
            <select {...register("branch_id")} className={inputClass(errors.branch_id)}>
              <option value="">Select branch</option>
              {branches.map((b) => (
                <option key={b.id} value={b.id}>{b.name} — {b.city}</option>
              ))}
            </select>
          </FormField>

          <FormField label="Reporting Manager" required error={errors.reporting_manager_id?.message}>
            <select {...register("reporting_manager_id")} className={inputClass(errors.reporting_manager_id)}>
              <option value="">Select manager</option>
              {managers.map((m) => (
                <option key={m.id} value={m.id}>{m.full_name} — {m.designation}</option>
              ))}
            </select>
          </FormField>

          <FormField label="Cost Center" error={errors.cost_center?.message}>
            <input
              {...register("cost_center")}
              type="text"
              placeholder="CC-IT-001"
              className={inputClass(errors.cost_center)}
            />
          </FormField>
        </div>
      </div>

      {/* ── Contract & Schedule ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Contract & Schedule
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField label="Contract Type" required error={errors.contract_type?.message}>
            <select {...register("contract_type")} className={inputClass(errors.contract_type)}>
              <option value="">Select contract type</option>
              <option value="permanent">Permanent</option>
              <option value="fixed_term">Fixed Term</option>
              <option value="probation">Probation</option>
              <option value="intern">Intern / Trainee</option>
              <option value="consultant">Consultant</option>
            </select>
          </FormField>

          <FormField label="Work Schedule" required error={errors.work_schedule?.message}>
            <select {...register("work_schedule")} className={inputClass(errors.work_schedule)}>
              <option value="">Select work schedule</option>
              <option value="full_time">Full Time</option>
              <option value="part_time">Part Time</option>
              <option value="remote">Fully Remote</option>
              <option value="hybrid">Hybrid</option>
            </select>
          </FormField>

          <FormField label="Joining Date" required error={errors.joining_date?.message}>
            <input
              {...register("joining_date")}
              type="date"
              className={inputClass(errors.joining_date)}
            />
          </FormField>

          {(contractType === "probation" || contractType === "fixed_term") && (
            <FormField
              label={contractType === "probation" ? "Probation End Date" : "Contract End Date"}
              error={errors.probation_end_date?.message}
            >
              <input
                {...register("probation_end_date")}
                type="date"
                className={inputClass(errors.probation_end_date)}
              />
            </FormField>
          )}

          {contractType === "probation" && (
            <FormField label="Confirmation Date" error={errors.confirmation_date?.message}>
              <input
                {...register("confirmation_date")}
                type="date"
                className={inputClass(errors.confirmation_date)}
              />
            </FormField>
          )}

          <FormField
            label="Notice Period (Days)"
            error={errors.notice_period_days?.message}
          >
            <input
              {...register("notice_period_days")}
              type="number"
              min={0}
              max={365}
              placeholder="30"
              className={inputClass(errors.notice_period_days)}
            />
          </FormField>
        </div>
      </div>

      {/* ── Shift & Timezone ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Shift & Timezone
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField label="Shift" error={errors.shift_id?.message}>
            <select {...register("shift_id")} className={inputClass(errors.shift_id)}>
              <option value="">Select shift (optional)</option>
              {shifts.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.start_time} – {s.end_time})
                </option>
              ))}
            </select>
          </FormField>

          <FormField label="Work Location Type" error={errors.work_location?.message}>
            <select {...register("work_location")} className={inputClass(errors.work_location)}>
              <option value="office">Office</option>
              <option value="remote">Remote</option>
              <option value="hybrid">Hybrid</option>
              <option value="field">Field</option>
            </select>
          </FormField>

          <FormField label="Timezone" error={errors.timezone?.message}>
            <select {...register("timezone")} className={inputClass(errors.timezone)}>
              {TIMEZONES.map((tz) => (
                <option key={tz} value={tz}>{tz}</option>
              ))}
            </select>
          </FormField>
        </div>
      </div>
    </div>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function inputClass(error?: { message?: string }) {
  const base =
    "block w-full rounded-lg border px-3 py-2.5 text-sm shadow-sm transition-colors focus:outline-none focus:ring-2";
  return error
    ? `${base} border-red-300 bg-red-50 text-red-900 focus:border-red-400 focus:ring-red-200`
    : `${base} border-gray-300 bg-white text-gray-900 focus:border-blue-400 focus:ring-blue-100`;
}

function FormField({
  label,
  required,
  hint,
  error,
  children,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {children}
      {hint && !error && <p className="mt-1 text-xs text-gray-500">{hint}</p>}
      {error && (
        <p className="mt-1 text-xs text-red-600 flex items-center gap-1">
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
          {error}
        </p>
      )}
    </div>
  );
}
