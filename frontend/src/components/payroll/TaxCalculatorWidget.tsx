'use client';

import { useState, useMemo } from 'react';
import { Calculator } from 'lucide-react';

import { Input }  from '@/components/ui/input';
import { Label }  from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';

import { useTaxSlabs } from '@/hooks/usePayroll';

function fmt(n: number) {
  return new Intl.NumberFormat('en-PK', { maximumFractionDigits: 0 }).format(n);
}

// Hardcoded FBR 2024-25 slabs for client-side calculation (mirrors backend defaults)
const FBR_SLABS = [
  { min: 0,         max: 600_000,     fixed: 0,         rate: 0.00, label: '0%' },
  { min: 600_001,   max: 1_200_000,   fixed: 0,         rate: 0.05, label: '5%' },
  { min: 1_200_001, max: 2_400_000,   fixed: 30_000,    rate: 0.15, label: '15%' },
  { min: 2_400_001, max: 3_600_000,   fixed: 210_000,   rate: 0.25, label: '25%' },
  { min: 3_600_001, max: 6_000_000,   fixed: 510_000,   rate: 0.30, label: '30%' },
  { min: 6_000_001, max: Infinity,    fixed: 1_230_000, rate: 0.35, label: '35%' },
];

function calcTax(annualSalary: number): { annualTax: number; monthlyTax: number; effectiveRate: number; slabIdx: number } {
  if (annualSalary <= 0) return { annualTax: 0, monthlyTax: 0, effectiveRate: 0, slabIdx: 0 };

  let annualTax = 0;
  let slabIdx   = 0;
  for (let i = 0; i < FBR_SLABS.length; i++) {
    const slab = FBR_SLABS[i];
    if (annualSalary >= slab.min) {
      const excess  = annualSalary - (slab.min - 1);
      annualTax     = slab.fixed + Math.floor(excess * slab.rate);
      slabIdx       = i;
    }
    if (annualSalary <= slab.max) break;
  }

  const monthlyTax    = Math.ceil(annualTax / 12);
  const effectiveRate = annualSalary > 0 ? annualTax / annualSalary : 0;
  return { annualTax, monthlyTax, effectiveRate, slabIdx };
}

interface Props {
  year?: number;
}

export function TaxCalculatorWidget({ year = 2025 }: Props) {
  const [monthly, setMonthly]   = useState('');
  const { data: dbSlabs = [] }  = useTaxSlabs(year);

  const monthlyNum  = Number(monthly.replace(/,/g, '')) || 0;
  const annualGross = monthlyNum * 12;

  const { annualTax, monthlyTax, effectiveRate, slabIdx } = useMemo(
    () => calcTax(annualGross),
    [annualGross],
  );

  return (
    <div className="space-y-6">
      {/* Input */}
      <Card className="border-0 shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Calculator className="h-4.5 w-4.5 text-blue-600" />
            Income Tax Calculator (FBR {year}–{year + 1})
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>Monthly Gross Salary (PKR)</Label>
              <Input
                type="text"
                placeholder="e.g. 150,000"
                value={monthly}
                onChange={(e) => setMonthly(e.target.value)}
                className="text-base font-medium"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Annual Gross Salary</Label>
              <div className="h-10 flex items-center px-3 bg-slate-50 rounded-md border border-slate-200 text-sm font-medium text-slate-700">
                PKR {fmt(annualGross)}
              </div>
            </div>
          </div>

          {monthlyNum > 0 && (
            <div className="grid gap-3 sm:grid-cols-3 mt-2">
              <ResultCard
                label="Monthly Tax"
                value={`PKR ${fmt(monthlyTax)}`}
                color="text-red-600"
              />
              <ResultCard
                label="Annual Tax"
                value={`PKR ${fmt(annualTax)}`}
                color="text-amber-600"
              />
              <ResultCard
                label="Effective Rate"
                value={`${(effectiveRate * 100).toFixed(2)}%`}
                color="text-blue-600"
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Slab Breakdown Table */}
      <Card className="border-0 shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm text-slate-700">FBR Tax Slabs {year}–{year + 1}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50">
                <TableHead>Annual Income Range</TableHead>
                <TableHead>Fixed Tax</TableHead>
                <TableHead>Rate on Excess</TableHead>
                <TableHead className="text-right">Your Tax (Annual)</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {FBR_SLABS.map((slab, i) => {
                const isActive = i === slabIdx && monthlyNum > 0;
                return (
                  <TableRow
                    key={i}
                    className={isActive ? 'bg-blue-50 font-medium' : ''}
                  >
                    <TableCell>
                      PKR {fmt(slab.min)}
                      {slab.max === Infinity ? '+' : ` – PKR ${fmt(slab.max)}`}
                      {isActive && (
                        <span className="ml-2 text-xs text-blue-600 font-medium">(your bracket)</span>
                      )}
                    </TableCell>
                    <TableCell>PKR {fmt(slab.fixed)}</TableCell>
                    <TableCell>{slab.label}</TableCell>
                    <TableCell className="text-right">
                      {isActive ? `PKR ${fmt(annualTax)}` : '—'}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {dbSlabs.length > 0 && (
        <p className="text-xs text-slate-500">
          * Custom tax slabs for {year} configured in your organisation override the defaults above.
        </p>
      )}
    </div>
  );
}

function ResultCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className={`text-xl font-bold ${color}`}>{value}</p>
    </div>
  );
}
