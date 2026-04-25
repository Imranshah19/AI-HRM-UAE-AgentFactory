'use client';

import { Info } from 'lucide-react';
import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from '@/components/ui/tooltip';
import { Separator } from '@/components/ui/separator';
import { cn }        from '@/lib/utils';
import type { SalaryStructure } from '@/types/employee';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmt(amount: number): string {
  return new Intl.NumberFormat('en-PK', {
    style:    'currency',
    currency: 'PKR',
    maximumFractionDigits: 0,
  }).format(amount);
}

function Row({
  label,
  amount,
  bold,
  positive,
  negative,
  tooltip,
}: {
  label:    string;
  amount:   number;
  bold?:    boolean;
  positive?: boolean;
  negative?: boolean;
  tooltip?:  string;
}) {
  return (
    <div className={cn('flex items-center justify-between py-1.5', bold && 'font-semibold')}>
      <span className={cn(
        'flex items-center gap-1 text-sm',
        bold ? 'text-slate-800 dark:text-slate-100' : 'text-slate-600 dark:text-slate-400',
      )}>
        {label}
        {tooltip && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Info className="h-3.5 w-3.5 text-slate-400 cursor-help" />
              </TooltipTrigger>
              <TooltipContent className="max-w-xs text-xs">{tooltip}</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </span>
      <span className={cn(
        'text-sm tabular-nums',
        bold     ? 'text-slate-900 dark:text-slate-50' : 'text-slate-700 dark:text-slate-300',
        positive && 'text-green-600',
        negative && 'text-red-600',
      )}>
        {fmt(amount)}
      </span>
    </div>
  );
}

// ─── FBR slab tooltip ─────────────────────────────────────────────────────────

const FBR_TOOLTIP =
  `FBR Tax Slabs (FY 2024-25):
• Up to Rs 600,000 → 0%
• Rs 600,001 – 1,200,000 → 5%
• Rs 1,200,001 – 2,400,000 → 15% (on excess)
• Rs 2,400,001 – 3,600,000 → 25%
• Above Rs 3,600,000 → 35%
Tax shown is an estimate; consult HR for exact withholding.`;

// ─── Component ────────────────────────────────────────────────────────────────

interface SalaryBreakdownCardProps {
  salary:    SalaryStructure;
  className?: string;
}

export function SalaryBreakdownCard({ salary, className }: SalaryBreakdownCardProps) {
  const totalAllowances =
    (salary.house_rent_allowance  ?? 0) +
    (salary.medical_allowance     ?? 0) +
    (salary.transport_allowance   ?? 0) +
    Object.values(salary.other_allowances ?? {}).reduce((s, v) => s + (v ?? 0), 0);

  const grossSalary   = (salary.basic_salary ?? 0) + totalAllowances;

  // Rough statutory deductions
  const eobi  = salary.eobi_applicable   ? Math.round(grossSalary * 0.01) : 0;
  const sessi = salary.sessi_applicable  ? Math.round(grossSalary * 0.0075) : 0;

  // Rough FBR estimate (annual ÷ 12)
  let annualTax = 0;
  if (salary.income_tax_applicable) {
    const annualGross = grossSalary * 12;
    if      (annualGross <= 600_000)       annualTax = 0;
    else if (annualGross <= 1_200_000)     annualTax = (annualGross - 600_000) * 0.05;
    else if (annualGross <= 2_400_000)     annualTax = 30_000 + (annualGross - 1_200_000) * 0.15;
    else if (annualGross <= 3_600_000)     annualTax = 210_000 + (annualGross - 2_400_000) * 0.25;
    else                                   annualTax = 510_000 + (annualGross - 3_600_000) * 0.35;
  }
  const monthlyTax    = Math.round(annualTax / 12);
  const totalDeductions = eobi + sessi + monthlyTax;
  const netSalary       = grossSalary - totalDeductions;

  return (
    <div className={cn('rounded-lg border bg-white dark:bg-slate-900 p-4 space-y-1', className)}>
      <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2">
        Salary Breakdown
      </h4>

      {/* Earnings */}
      <p className="text-[11px] uppercase tracking-wider text-slate-400 font-medium">Earnings</p>
      <Row label="Basic Salary"           amount={salary.basic_salary ?? 0} />
      <Row label="House Rent Allowance"   amount={salary.house_rent_allowance ?? 0} />
      <Row label="Medical Allowance"      amount={salary.medical_allowance ?? 0} />
      <Row label="Transport Allowance"    amount={salary.transport_allowance ?? 0} />
      {Object.entries(salary.other_allowances ?? {}).map(([key, val]) => (
        <Row key={key} label={key} amount={val ?? 0} />
      ))}
      <Separator className="my-1" />
      <Row label="Gross Salary" amount={grossSalary} bold positive />

      {/* Deductions */}
      {totalDeductions > 0 && (
        <>
          <p className="text-[11px] uppercase tracking-wider text-slate-400 font-medium mt-3">
            Deductions
          </p>
          {eobi > 0 && (
            <Row label="EOBI (1%)"  amount={eobi}  negative
              tooltip="Employees' Old-Age Benefits Institution — 1% of gross salary." />
          )}
          {sessi > 0 && (
            <Row label="SESSI (0.75%)" amount={sessi} negative
              tooltip="Sindh Employees Social Security Institution — 0.75% of gross salary." />
          )}
          {monthlyTax > 0 && (
            <Row label="Income Tax (est.)" amount={monthlyTax} negative tooltip={FBR_TOOLTIP} />
          )}
          <Separator className="my-1" />
          <Row label="Total Deductions" amount={totalDeductions} bold negative />
        </>
      )}

      {/* Net */}
      <Separator className="my-1" />
      <Row label="Net Take-Home" amount={netSalary} bold />

      {salary.effective_from && (
        <p className="text-[11px] text-slate-400 mt-2">
          Effective from {new Date(salary.effective_from).toLocaleDateString('en-PK', {
            day: '2-digit', month: 'short', year: 'numeric',
          })}
        </p>
      )}
    </div>
  );
}
