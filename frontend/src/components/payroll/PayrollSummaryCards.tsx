'use client';

import { TrendingUp, TrendingDown, Minus, DollarSign, Users, PiggyBank, Receipt } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import type { PayrollRun } from '@/types/payroll';

interface Props {
  current:  PayrollRun;
  previous?: PayrollRun | null;
}

function fmt(n: number): string {
  return new Intl.NumberFormat('en-PK', { maximumFractionDigits: 0 }).format(n);
}

function Delta({ current, previous }: { current: number; previous?: number }) {
  if (!previous || previous === 0) return null;
  const pct = ((current - previous) / previous) * 100;
  if (Math.abs(pct) < 0.1) return <Minus className="h-3.5 w-3.5 text-slate-400" />;
  return pct > 0
    ? <span className="flex items-center gap-0.5 text-xs text-red-500">
        <TrendingUp className="h-3 w-3" />{pct.toFixed(1)}%
      </span>
    : <span className="flex items-center gap-0.5 text-xs text-green-600">
        <TrendingDown className="h-3 w-3" />{Math.abs(pct).toFixed(1)}%
      </span>;
}

interface Metric {
  label:   string;
  value:   number;
  prev?:   number;
  icon:    React.ReactNode;
  color:   string;
  prefix?: string;
}

export function PayrollSummaryCards({ current, previous }: Props) {
  const metrics: Metric[] = [
    {
      label:  'Total Gross',
      value:  current.total_gross,
      prev:   previous?.total_gross,
      icon:   <DollarSign className="h-5 w-5" />,
      color:  'text-blue-600 bg-blue-50',
      prefix: 'PKR ',
    },
    {
      label:  'Total Deductions',
      value:  current.total_deductions,
      prev:   previous?.total_deductions,
      icon:   <Receipt className="h-5 w-5" />,
      color:  'text-amber-600 bg-amber-50',
      prefix: 'PKR ',
    },
    {
      label:  'Income Tax',
      value:  current.total_income_tax,
      prev:   previous?.total_income_tax,
      icon:   <PiggyBank className="h-5 w-5" />,
      color:  'text-purple-600 bg-purple-50',
      prefix: 'PKR ',
    },
    {
      label:  'Net Payable',
      value:  current.total_net,
      prev:   previous?.total_net,
      icon:   <Users className="h-5 w-5" />,
      color:  'text-green-600 bg-green-50',
      prefix: 'PKR ',
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {metrics.map((m) => (
        <Card key={m.label} className="border-0 shadow-sm">
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">{m.label}</p>
                <p className="mt-1 text-xl font-bold text-slate-800">
                  {m.prefix}{fmt(m.value)}
                </p>
                <div className="mt-1 h-4">
                  <Delta current={m.value} previous={m.prev} />
                </div>
              </div>
              <span className={`p-2 rounded-lg ${m.color}`}>{m.icon}</span>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
