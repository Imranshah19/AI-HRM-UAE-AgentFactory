"use client";

import React, { useMemo } from "react";
import { UseFormReturn, useWatch } from "react-hook-form";
import { AddEmployeeFormData } from "@/schemas/employee.schema";
import { SalaryBreakdown, SalaryStructure } from "@/types/employee.types";

interface Props {
  form: UseFormReturn<AddEmployeeFormData>;
  salaryStructures: SalaryStructure[];
}

const CURRENCIES = ["PKR", "USD", "AED", "SAR", "GBP", "EUR", "INR", "BDT"];
const BANKS = [
  "HBL – Habib Bank Limited",
  "UBL – United Bank Limited",
  "MCB Bank",
  "Allied Bank",
  "Bank Alfalah",
  "Meezan Bank",
  "Standard Chartered",
  "Faysal Bank",
  "Silk Bank",
  "JS Bank",
  "Other",
];

const EOBI_RATE = 0.05;    // 5% employer + employee
const SESSI_RATE = 0.0125; // 1.25%

function computeSalary(values: Partial<AddEmployeeFormData>): SalaryBreakdown {
  const basic = Number(values.basic_salary) || 0;
  const hra   = Number(values.house_rent_allowance) || 0;
  const med   = Number(values.medical_allowance) || 0;
  const trans = Number(values.transport_allowance) || 0;
  const fuel  = Number(values.fuel_allowance) || 0;
  const util  = Number(values.utility_allowance) || 0;
  const other = Number(values.other_allowances) || 0;

  const total_allowances = hra + med + trans + fuel + util + other;
  const gross = basic + total_allowances;

  const eobi  = values.eobi_applicable  ? Math.round(basic * EOBI_RATE)  : 0;
  const sessi = values.sessi_applicable ? Math.round(basic * SESSI_RATE) : 0;

  // Simplified tax slab (Pakistan FY 2025-26)
  let tax = 0;
  const annualGross = gross * 12;
  if (annualGross > 3_600_000)      tax = Math.round(((annualGross - 3_600_000) * 0.35 + 405_000) / 12);
  else if (annualGross > 2_400_000) tax = Math.round(((annualGross - 2_400_000) * 0.30 + 225_000) / 12);
  else if (annualGross > 1_200_000) tax = Math.round(((annualGross - 1_200_000) * 0.175 + 15_000) / 12);
  else if (annualGross > 600_000)   tax = Math.round(((annualGross - 600_000) * 0.025) / 12);

  const totalDeductions = eobi + sessi + (values.income_tax_applicable ? tax : 0);

  return {
    gross_salary: gross,
    basic_salary: basic,
    total_allowances,
    house_rent_allowance: hra,
    medical_allowance: med,
    transport_allowance: trans,
    fuel_allowance: fuel,
    utility_allowance: util,
    other_allowances: other,
    eobi_deduction: eobi,
    sessi_deduction: sessi,
    estimated_income_tax: values.income_tax_applicable ? tax : 0,
    net_salary: gross - totalDeductions,
  };
}

function fmt(n: number, currency = "PKR") {
  return new Intl.NumberFormat("en-PK", { style: "currency", currency, maximumFractionDigits: 0 }).format(n);
}

export default function Step3Compensation({ form, salaryStructures }: Props) {
  const { register, formState: { errors }, control } = form;

  const watched = useWatch({ control });
  const breakdown = useMemo(() => computeSalary(watched as Partial<AddEmployeeFormData>), [watched]);
  const currency = watched.currency || "PKR";

  return (
    <div className="space-y-8">
      {/* ── Salary Structure Preset ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Salary Structure
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <FormField label="Currency" error={errors.currency?.message}>
            <select {...register("currency")} className={inputClass(errors.currency)}>
              {CURRENCIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </FormField>

          <FormField label="Apply Preset Structure" error={errors.salary_structure_id?.message}>
            <select {...register("salary_structure_id")} className={inputClass(errors.salary_structure_id)}>
              <option value="">None — enter manually</option>
              {salaryStructures.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </FormField>

          <FormField label="Effective Date" required error={errors.effective_date?.message}>
            <input
              {...register("effective_date")}
              type="date"
              className={inputClass(errors.effective_date)}
            />
          </FormField>
        </div>
      </div>

      {/* ── Basic Salary & Allowances ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Basic Salary & Allowances
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <FormField label="Basic Salary" required error={errors.basic_salary?.message}>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400 text-sm font-medium">
                {currency}
              </span>
              <input
                {...register("basic_salary")}
                type="number"
                min={0}
                placeholder="50,000"
                className={`${inputClass(errors.basic_salary)} pl-14`}
              />
            </div>
          </FormField>

          <FormField label="House Rent Allowance" error={errors.house_rent_allowance?.message}>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400 text-sm font-medium">{currency}</span>
              <input {...register("house_rent_allowance")} type="number" min={0} placeholder="0" className={`${inputClass(errors.house_rent_allowance)} pl-14`} />
            </div>
          </FormField>

          <FormField label="Medical Allowance" error={errors.medical_allowance?.message}>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400 text-sm font-medium">{currency}</span>
              <input {...register("medical_allowance")} type="number" min={0} placeholder="0" className={`${inputClass(errors.medical_allowance)} pl-14`} />
            </div>
          </FormField>

          <FormField label="Transport Allowance" error={errors.transport_allowance?.message}>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400 text-sm font-medium">{currency}</span>
              <input {...register("transport_allowance")} type="number" min={0} placeholder="0" className={`${inputClass(errors.transport_allowance)} pl-14`} />
            </div>
          </FormField>

          <FormField label="Fuel Allowance" error={errors.fuel_allowance?.message}>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400 text-sm font-medium">{currency}</span>
              <input {...register("fuel_allowance")} type="number" min={0} placeholder="0" className={`${inputClass(errors.fuel_allowance)} pl-14`} />
            </div>
          </FormField>

          <FormField label="Utility Allowance" error={errors.utility_allowance?.message}>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400 text-sm font-medium">{currency}</span>
              <input {...register("utility_allowance")} type="number" min={0} placeholder="0" className={`${inputClass(errors.utility_allowance)} pl-14`} />
            </div>
          </FormField>

          <FormField label="Other Allowances" error={errors.other_allowances?.message}>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400 text-sm font-medium">{currency}</span>
              <input {...register("other_allowances")} type="number" min={0} placeholder="0" className={`${inputClass(errors.other_allowances)} pl-14`} />
            </div>
          </FormField>
        </div>
      </div>

      {/* ── Deductions ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Statutory Deductions
        </h3>
        <div className="flex flex-wrap gap-6">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              {...register("eobi_applicable")}
              type="checkbox"
              className="w-4 h-4 rounded text-blue-600 border-gray-300 focus:ring-blue-500"
            />
            <div>
              <span className="text-sm font-medium text-gray-700">EOBI (5%)</span>
              <p className="text-xs text-gray-500">Employees' Old-Age Benefits Institution</p>
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              {...register("sessi_applicable")}
              type="checkbox"
              className="w-4 h-4 rounded text-blue-600 border-gray-300 focus:ring-blue-500"
            />
            <div>
              <span className="text-sm font-medium text-gray-700">SESSI (1.25%)</span>
              <p className="text-xs text-gray-500">Sindh Employees' Social Security Institution</p>
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              {...register("income_tax_applicable")}
              type="checkbox"
              className="w-4 h-4 rounded text-blue-600 border-gray-300 focus:ring-blue-500"
            />
            <div>
              <span className="text-sm font-medium text-gray-700">Income Tax (FBR Slabs)</span>
              <p className="text-xs text-gray-500">Auto-calculated based on gross salary</p>
            </div>
          </label>
        </div>
      </div>

      {/* ── Live Salary Breakdown ── */}
      <div className="rounded-xl border border-blue-100 bg-blue-50 p-5">
        <h3 className="text-sm font-semibold text-blue-700 uppercase tracking-wider mb-4">
          Live Salary Breakdown
        </h3>
        <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
          <BreakdownRow label="Basic Salary" value={fmt(breakdown.basic_salary, currency)} />
          <BreakdownRow label="Total Allowances" value={fmt(breakdown.total_allowances, currency)} />
          <BreakdownRow label="Gross Salary" value={fmt(breakdown.gross_salary, currency)} bold />
          <BreakdownRow label="EOBI Deduction" value={`– ${fmt(breakdown.eobi_deduction, currency)}`} red />
          <BreakdownRow label="SESSI Deduction" value={`– ${fmt(breakdown.sessi_deduction, currency)}`} red />
          <BreakdownRow label="Est. Income Tax" value={`– ${fmt(breakdown.estimated_income_tax, currency)}`} red />
        </div>
        <div className="mt-4 pt-4 border-t border-blue-200 flex justify-between items-center">
          <span className="text-sm font-semibold text-blue-800">Estimated Net Salary</span>
          <span className="text-lg font-bold text-blue-900">{fmt(breakdown.net_salary, currency)}</span>
        </div>
        <p className="mt-2 text-xs text-blue-600">
          * Tax calculated using Pakistan FBR slabs (FY 2025-26). Actual tax may vary.
        </p>
      </div>

      {/* ── Bank Details ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Bank Details
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField label="Payment Method" error={errors.payment_method?.message}>
            <select {...register("payment_method")} className={inputClass(errors.payment_method)}>
              <option value="bank_transfer">Bank Transfer</option>
              <option value="cash">Cash</option>
              <option value="cheque">Cheque</option>
            </select>
          </FormField>

          <FormField label="Bank Name" required error={errors.bank_name?.message}>
            <select {...register("bank_name")} className={inputClass(errors.bank_name)}>
              <option value="">Select bank</option>
              {BANKS.map((b) => (
                <option key={b} value={b}>{b}</option>
              ))}
            </select>
          </FormField>

          <FormField label="Account Title" required error={errors.bank_account_title?.message}>
            <input
              {...register("bank_account_title")}
              type="text"
              placeholder="Muhammad Ahmed"
              className={inputClass(errors.bank_account_title)}
            />
          </FormField>

          <FormField label="Account Number" required error={errors.bank_account_number?.message}>
            <input
              {...register("bank_account_number")}
              type="text"
              placeholder="0123456789012345"
              className={inputClass(errors.bank_account_number)}
            />
          </FormField>

          <FormField
            label="IBAN"
            hint="e.g. PK36SCBL0000001123456702"
            error={errors.bank_iban?.message}
          >
            <input
              {...register("bank_iban")}
              type="text"
              placeholder="PK36XXXX0000001234567890"
              className={inputClass(errors.bank_iban)}
            />
          </FormField>

          <FormField label="Branch Code" error={errors.bank_branch_code?.message}>
            <input
              {...register("bank_branch_code")}
              type="text"
              placeholder="0123"
              className={inputClass(errors.bank_branch_code)}
            />
          </FormField>
        </div>
      </div>
    </div>
  );
}

// ─── Sub-components ────────────────────────────────────────────────────────────

function BreakdownRow({
  label,
  value,
  bold,
  red,
}: {
  label: string;
  value: string;
  bold?: boolean;
  red?: boolean;
}) {
  return (
    <div className="flex justify-between items-center py-1 px-2 rounded">
      <span className={`text-xs ${red ? "text-red-600" : "text-blue-700"}`}>{label}</span>
      <span className={`text-xs font-medium ${bold ? "text-blue-900 font-bold" : red ? "text-red-700" : "text-blue-800"}`}>
        {value}
      </span>
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
