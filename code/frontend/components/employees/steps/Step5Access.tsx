"use client";

import React from "react";
import { UseFormReturn, useWatch } from "react-hook-form";
import { AddEmployeeFormData } from "@/schemas/employee.schema";
import { Role, Employee } from "@/types/employee.types";

interface Props {
  form: UseFormReturn<AddEmployeeFormData>;
  roles: Role[];
  employees: Employee[];
}

const MODULES: { id: string; label: string; description: string; icon: string }[] = [
  { id: "employee_management",  label: "Employee Management",    description: "View/edit employee records",        icon: "👥" },
  { id: "attendance",           label: "Attendance & Time",      description: "Clock-in/out, timesheets",          icon: "🕐" },
  { id: "payroll",              label: "Payroll",                description: "Salary slips, payroll runs",        icon: "💰" },
  { id: "leave",                label: "Leave Management",       description: "Apply/approve leave requests",      icon: "🏖️" },
  { id: "performance",          label: "Performance",            description: "Goals, KPIs, appraisals",           icon: "📊" },
  { id: "recruitment",          label: "Recruitment (ATS)",      description: "Job postings, applications",        icon: "🎯" },
  { id: "training",             label: "Training & LMS",         description: "Courses, certifications",           icon: "📚" },
  { id: "self_service",         label: "Self-Service Portal",    description: "Personal docs, requests",           icon: "🙋" },
  { id: "assets",               label: "Asset Management",       description: "Assigned IT/office assets",         icon: "💼" },
  { id: "offboarding",          label: "Offboarding",            description: "Exit process, clearance",           icon: "🚪" },
  { id: "compliance",           label: "Compliance & Legal",     description: "Documents, audit logs",             icon: "⚖️" },
  { id: "analytics",            label: "BI & Analytics",         description: "Reports, dashboards",               icon: "📈" },
  { id: "notifications",        label: "Notifications",          description: "Alerts, reminders",                 icon: "🔔" },
  { id: "mobile",               label: "Mobile App",             description: "Full mobile access",                icon: "📱" },
];

export default function Step5Access({ form, roles, employees }: Props) {
  const { register, setValue, watch, formState: { errors }, control } = form;

  const selectedModules: string[] = useWatch({ control, name: "modules_access" }) || [];
  const laptopReq    = useWatch({ control, name: "laptop_required" });
  const simReq       = useWatch({ control, name: "sim_card_required" });
  const accessReq    = useWatch({ control, name: "access_card_required" });
  const parkingReq   = useWatch({ control, name: "parking_slot_required" });
  const sendWelcome  = useWatch({ control, name: "send_welcome_email" });
  const sendCreds    = useWatch({ control, name: "send_portal_credentials" });

  const toggleModule = (moduleId: string) => {
    const updated = selectedModules.includes(moduleId)
      ? selectedModules.filter((m) => m !== moduleId)
      : [...selectedModules, moduleId];
    setValue("modules_access", updated, { shouldValidate: true });
  };

  const selectAllModules = () => setValue("modules_access", MODULES.map((m) => m.id), { shouldValidate: true });
  const clearAllModules  = () => setValue("modules_access", [], { shouldValidate: true });

  return (
    <div className="space-y-8">
      {/* ── Role Assignment ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          System Role
        </h3>
        <div className="max-w-sm">
          <FormField label="Assign Role" required error={errors.role_id?.message}>
            <select {...register("role_id")} className={inputClass(errors.role_id)}>
              <option value="">Select role</option>
              {roles.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} — {r.description}
                </option>
              ))}
            </select>
          </FormField>
        </div>
      </div>

      {/* ── Module Access ── */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
            Module Access
            <span className="ml-2 text-xs font-normal text-gray-400 normal-case tracking-normal">
              ({selectedModules.length} of {MODULES.length} selected)
            </span>
          </h3>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={selectAllModules}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium"
            >
              Select all
            </button>
            <span className="text-gray-300">|</span>
            <button
              type="button"
              onClick={clearAllModules}
              className="text-xs text-gray-500 hover:text-gray-600"
            >
              Clear all
            </button>
          </div>
        </div>

        {errors.modules_access && (
          <p className="mb-3 text-xs text-red-600 flex items-center gap-1">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            {(errors.modules_access as { message?: string }).message}
          </p>
        )}

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {MODULES.map((mod) => {
            const checked = selectedModules.includes(mod.id);
            return (
              <label
                key={mod.id}
                className={`
                  flex items-start gap-3 rounded-lg border p-3 cursor-pointer transition-colors
                  ${checked
                    ? "border-blue-300 bg-blue-50"
                    : "border-gray-200 bg-white hover:border-blue-200 hover:bg-blue-50/40"
                  }
                `}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleModule(mod.id)}
                  className="mt-0.5 w-4 h-4 rounded text-blue-600 border-gray-300 focus:ring-blue-500"
                />
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-base">{mod.icon}</span>
                    <span className={`text-sm font-medium ${checked ? "text-blue-800" : "text-gray-700"}`}>
                      {mod.label}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{mod.description}</p>
                </div>
              </label>
            );
          })}
        </div>
      </div>

      {/* ── Work Email ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Email & Communication
        </h3>
        <div className="space-y-3">
          <ToggleRow
            label="Create Work Email Account"
            description="Auto-provision corporate email on joining"
            field="create_work_email"
            checked={useWatch({ control, name: "create_work_email" })}
            register={register}
          />
        </div>
      </div>

      {/* ── IT Assets ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          IT & Office Assets Required
        </h3>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <ToggleRow label="Laptop / Computer" description="Issue laptop on joining day" field="laptop_required" checked={laptopReq} register={register} />
          <ToggleRow label="SIM Card" description="Corporate mobile number" field="sim_card_required" checked={simReq} register={register} />
          <ToggleRow label="Access Card" description="Building / floor access card" field="access_card_required" checked={accessReq} register={register} />
          <ToggleRow label="Parking Slot" description="Reserved parking space" field="parking_slot_required" checked={parkingReq} register={register} />
        </div>
      </div>

      {/* ── Onboarding ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Onboarding Setup
        </h3>
        <div className="space-y-3 mb-4">
          <ToggleRow label="Send Welcome Email" description="Automated welcome message on joining" field="send_welcome_email" checked={sendWelcome} register={register} />
          <ToggleRow label="Send Portal Credentials" description="Login details for employee self-service portal" field="send_portal_credentials" checked={sendCreds} register={register} />
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField label="Onboarding Checklist Template" error={errors.onboarding_checklist_template_id?.message}>
            <select
              {...register("onboarding_checklist_template_id")}
              className={inputClass(errors.onboarding_checklist_template_id)}
            >
              <option value="">Select template (optional)</option>
              <option value="standard">Standard Onboarding</option>
              <option value="it_staff">IT Staff Onboarding</option>
              <option value="sales">Sales Team Onboarding</option>
              <option value="remote">Remote Employee Onboarding</option>
              <option value="intern">Intern Onboarding</option>
            </select>
          </FormField>

          <FormField label="Onboarding Buddy" error={errors.buddy_employee_id?.message}>
            <select
              {...register("buddy_employee_id")}
              className={inputClass(errors.buddy_employee_id)}
            >
              <option value="">Assign buddy (optional)</option>
              {employees.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.full_name} — {e.designation}
                </option>
              ))}
            </select>
          </FormField>
        </div>
      </div>

      {/* ── HR Notes ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Internal HR Notes
        </h3>
        <FormField
          label="Notes"
          hint="Visible to HR only. Max 1000 characters."
          error={(errors.hr_notes as { message?: string })?.message}
        >
          <textarea
            {...register("hr_notes")}
            rows={4}
            placeholder="Any additional notes about this employee or onboarding requirements..."
            className={`${inputClass(errors.hr_notes)} resize-none`}
          />
        </FormField>
      </div>
    </div>
  );
}

// ─── Sub-components ────────────────────────────────────────────────────────────

function ToggleRow({
  label,
  description,
  field,
  checked,
  register,
}: {
  label: string;
  description: string;
  field: keyof AddEmployeeFormData;
  checked: boolean;
  register: UseFormReturn<AddEmployeeFormData>["register"];
}) {
  return (
    <label className={`
      flex items-center justify-between rounded-lg border p-3 cursor-pointer transition-colors
      ${checked ? "border-blue-200 bg-blue-50" : "border-gray-200 bg-white hover:border-gray-300"}
    `}>
      <div>
        <span className={`text-sm font-medium ${checked ? "text-blue-800" : "text-gray-700"}`}>
          {label}
        </span>
        <p className="text-xs text-gray-500 mt-0.5">{description}</p>
      </div>
      <div className="relative ml-4">
        <input
          {...register(field)}
          type="checkbox"
          className="sr-only peer"
        />
        <div className={`
          w-10 h-6 rounded-full transition-colors
          ${checked ? "bg-blue-600" : "bg-gray-200"}
        `} />
        <div className={`
          absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform
          ${checked ? "translate-x-4" : "translate-x-0"}
        `} />
      </div>
    </label>
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
