'use client';

import { useState, useEffect } from 'react';
import { AlertTriangle, Calendar, ChevronDown } from 'lucide-react';

import { Button }   from '@/components/ui/button';
import { Label }    from '@/components/ui/label';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';

import { useRunPayroll, usePayrollRuns } from '@/hooks/usePayroll';

interface Props {
  open:    boolean;
  onClose: () => void;
}

const MONTHS = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December',
];

const currentYear  = new Date().getFullYear();
const currentMonth = new Date().getMonth() + 1;  // 1-based
const YEARS        = Array.from({ length: 4 }, (_, i) => currentYear - i);

export function RunPayrollDialog({ open, onClose }: Props) {
  const [month, setMonth] = useState(currentMonth);
  const [year,  setYear]  = useState(currentYear);

  const runPayroll = useRunPayroll();
  const { data: runs } = usePayrollRuns({ year });

  const alreadyRun = runs?.results?.some(
    (r) => r.month === month && r.year === year
  );

  const handleSubmit = () => {
    if (alreadyRun) return;
    runPayroll.mutate(
      { month, year, department_ids: null, notes: null },
      { onSuccess: () => onClose() },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-blue-600" />
            Run Payroll
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>Month</Label>
              <Select
                value={String(month)}
                onValueChange={(v) => setMonth(Number(v))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MONTHS.map((m, i) => (
                    <SelectItem key={i} value={String(i + 1)}>
                      {m}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label>Year</Label>
              <Select
                value={String(year)}
                onValueChange={(v) => setYear(Number(v))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {YEARS.map((y) => (
                    <SelectItem key={y} value={String(y)}>
                      {y}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {alreadyRun && (
            <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3">
              <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
              <p className="text-sm text-amber-800">
                Payroll for <strong>{MONTHS[month - 1]} {year}</strong> has already been run.
                You cannot run payroll twice for the same month.
              </p>
            </div>
          )}

          {!alreadyRun && (
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
              <p className="text-sm text-blue-800">
                This will process payroll for <strong>all active employees</strong> for{' '}
                <strong>{MONTHS[month - 1]} {year}</strong>. Processing runs asynchronously
                and may take a few minutes.
              </p>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onClose} disabled={runPayroll.isPending}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={alreadyRun || runPayroll.isPending}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {runPayroll.isPending ? 'Starting…' : `Run ${MONTHS[month - 1]} ${year} Payroll`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
