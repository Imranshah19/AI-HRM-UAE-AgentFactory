'use client';

import { useState } from 'react';
import { CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';

import { Button }   from '@/components/ui/button';
import { Label }    from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';

import { useApprovePayroll, useRejectPayroll } from '@/hooks/usePayroll';
import type { PayrollRun } from '@/types/payroll';

interface Props {
  open:    boolean;
  action:  'approve' | 'reject';
  run:     PayrollRun;
  onClose: () => void;
}

function fmt(n: number) {
  return new Intl.NumberFormat('en-PK', { maximumFractionDigits: 0 }).format(n);
}

const MONTHS = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December',
];

export function PayrollApprovalDialog({ open, action, run, onClose }: Props) {
  const [notes, setNotes] = useState('');

  const approveMutation = useApprovePayroll();
  const rejectMutation  = useRejectPayroll();

  const isPending = approveMutation.isPending || rejectMutation.isPending;
  const isReject  = action === 'reject';

  const handleSubmit = () => {
    if (isReject && !notes.trim()) return;

    const payload = { action, notes: notes.trim() || null };

    if (isReject) {
      rejectMutation.mutate(
        { id: run.id, payload },
        { onSuccess: () => { setNotes(''); onClose(); } },
      );
    } else {
      approveMutation.mutate(
        { id: run.id, payload },
        { onSuccess: () => { setNotes(''); onClose(); } },
      );
    }
  };

  return (
    <Dialog open={open} onOpenChange={() => { setNotes(''); onClose(); }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className={`flex items-center gap-2 ${isReject ? 'text-red-700' : 'text-green-700'}`}>
            {isReject
              ? <XCircle className="h-5 w-5" />
              : <CheckCircle2 className="h-5 w-5" />
            }
            {isReject ? 'Reject Payroll Run' : 'Approve Payroll Run'}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Summary */}
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-2">
            <p className="text-sm font-medium text-slate-700">
              {MONTHS[run.month - 1]} {run.year} Payroll
            </p>
            <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
              <span className="text-slate-500">Employees</span>
              <span className="font-medium">{run.total_employees}</span>
              <span className="text-slate-500">Total Gross</span>
              <span className="font-medium">PKR {fmt(run.total_gross)}</span>
              <span className="text-slate-500">Total Net</span>
              <span className="font-semibold text-green-700">PKR {fmt(run.total_net)}</span>
            </div>
          </div>

          {/* Impact notice */}
          {!isReject && (
            <div className="flex items-start gap-2 rounded-lg border border-green-200 bg-green-50 p-3">
              <CheckCircle2 className="h-4 w-4 text-green-600 mt-0.5 shrink-0" />
              <p className="text-sm text-green-800">
                Approving will generate <strong>{run.total_employees} payslips</strong> and send
                salary emails to all employees.
              </p>
            </div>
          )}

          {isReject && (
            <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3">
              <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 shrink-0" />
              <p className="text-sm text-red-800">
                Rejecting will <strong>delete all {run.total_employees} payroll records</strong>{' '}
                for this run. This cannot be undone.
              </p>
            </div>
          )}

          {/* Notes */}
          <div className="space-y-1.5">
            <Label htmlFor="notes">
              {isReject ? 'Rejection Reason *' : 'Notes (optional)'}
            </Label>
            <Textarea
              id="notes"
              placeholder={
                isReject
                  ? 'Please provide a reason for rejection…'
                  : 'Optional approval notes…'
              }
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className={isReject && !notes.trim() ? 'border-red-300' : ''}
            />
            {isReject && !notes.trim() && (
              <p className="text-xs text-red-500">Rejection reason is required.</p>
            )}
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onClose} disabled={isPending}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isPending || (isReject && !notes.trim())}
            className={isReject
              ? 'bg-red-600 hover:bg-red-700 text-white'
              : 'bg-green-600 hover:bg-green-700 text-white'
            }
          >
            {isPending
              ? (isReject ? 'Rejecting…' : 'Approving…')
              : (isReject ? 'Reject Payroll' : 'Approve Payroll')
            }
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
