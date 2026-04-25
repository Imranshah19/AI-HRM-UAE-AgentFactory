'use client';

import { useState } from 'react';
import { Download, ChevronDown, ChevronUp, BadgeCheck } from 'lucide-react';
import { format } from 'date-fns';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge }  from '@/components/ui/badge';

import { getPayslipPdfUrl } from '@/lib/api/payroll';
import type { PayrollRecord } from '@/types/payroll';

interface Props {
  record: PayrollRecord;
}

function fmt(n: number) {
  return new Intl.NumberFormat('en-PK', { maximumFractionDigits: 0 }).format(n);
}

const MONTHS = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December',
];

export function PayslipCard({ record }: Props) {
  const [expanded, setExpanded] = useState(false);

  // Derive month/year from created_at as a fallback
  const monthLabel = MONTHS[(record as any).month ? (record as any).month - 1 : 0];
  const yearLabel  = (record as any).year ?? new Date(record.created_at).getFullYear();

  const handleDownload = () => {
    const url = getPayslipPdfUrl(record.id);
    const a   = document.createElement('a');
    a.href    = url;
    a.download = `payslip_${monthLabel}_${yearLabel}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <Card className="border-0 shadow-sm hover:shadow-md transition-shadow">
      <CardContent className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">
              {monthLabel} {yearLabel}
            </p>
            <p className="mt-0.5 text-2xl font-bold text-slate-900">
              PKR {fmt(record.net_salary)}
            </p>
          </div>
          <Badge
            className={
              record.status === 'paid'
                ? 'bg-green-100 text-green-700 border-green-200'
                : 'bg-blue-100 text-blue-700 border-blue-200'
            }
            variant="outline"
          >
            {record.status === 'paid' && <BadgeCheck className="h-3 w-3 mr-1" />}
            {record.status.charAt(0).toUpperCase() + record.status.slice(1)}
          </Badge>
        </div>

        {/* Quick summary */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm mb-4">
          <span className="text-slate-500">Gross</span>
          <span className="font-medium text-right">PKR {fmt(record.gross_salary)}</span>
          <span className="text-slate-500">Deductions</span>
          <span className="font-medium text-right text-red-600">− PKR {fmt(record.total_deductions)}</span>
        </div>

        {/* Expanded breakdown */}
        {expanded && (
          <div className="border-t border-slate-100 pt-3 mt-2 space-y-2 text-sm">
            <p className="font-semibold text-slate-700 text-xs uppercase tracking-wide mb-1">Earnings</p>
            <Row label="Basic Salary"         value={record.basic_salary} />
            {record.house_rent_allowance > 0 &&
              <Row label="House Rent"          value={record.house_rent_allowance} />}
            {record.medical_allowance > 0 &&
              <Row label="Medical"             value={record.medical_allowance} />}
            {record.transport_allowance > 0 &&
              <Row label="Transport"           value={record.transport_allowance} />}
            {record.fuel_allowance > 0 &&
              <Row label="Fuel"                value={record.fuel_allowance} />}

            <p className="font-semibold text-slate-700 text-xs uppercase tracking-wide mb-1 pt-2">Deductions</p>
            {record.eobi_employee > 0 &&
              <Row label="EOBI (Employee)"     value={record.eobi_employee} negative />}
            {record.income_tax > 0 &&
              <Row label="Income Tax"          value={record.income_tax}   negative />}
            {record.loan_deduction > 0 &&
              <Row label="Loan Deduction"      value={record.loan_deduction} negative />}
            {record.advance_deduction > 0 &&
              <Row label="Advance Recovery"    value={record.advance_deduction} negative />}

            <p className="font-semibold text-slate-700 text-xs uppercase tracking-wide mb-1 pt-2">Attendance</p>
            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <Att label="Present" value={record.present_days} />
              <Att label="Absent"  value={record.absent_days} />
              <Att label="OT Hrs"  value={record.overtime_hours ?? 0} />
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2 mt-4">
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? <ChevronUp className="h-3.5 w-3.5 mr-1" /> : <ChevronDown className="h-3.5 w-3.5 mr-1" />}
            {expanded ? 'Hide' : 'Details'}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={handleDownload}
            disabled={!record.payslip_url}
          >
            <Download className="h-3.5 w-3.5 mr-1" />
            Download
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function Row({ label, value, negative = false }: { label: string; value: number; negative?: boolean }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-slate-500">{label}</span>
      <span className={`font-medium ${negative ? 'text-red-600' : ''}`}>
        {negative ? '− ' : ''}PKR {new Intl.NumberFormat('en-PK', { maximumFractionDigits: 0 }).format(value)}
      </span>
    </div>
  );
}

function Att({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded bg-slate-50 py-1.5 px-2">
      <p className="font-semibold text-slate-800">{value}</p>
      <p className="text-slate-500 mt-0.5">{label}</p>
    </div>
  );
}
