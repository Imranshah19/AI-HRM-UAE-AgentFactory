'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { format } from 'date-fns';
import { CheckCircle2, XCircle, Loader2, Calendar, Clock } from 'lucide-react';

import { Button }       from '@/components/ui/button';
import { Label }        from '@/components/ui/label';
import { Textarea }     from '@/components/ui/textarea';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import { EmployeeAvatar } from '@/components/employees/EmployeeAvatar';
import { cn }             from '@/lib/utils';
import type { LeaveRequestListItem, LeaveBalanceItem } from '@/types/leave';

// ─── Schema ───────────────────────────────────────────────────────────────────

const schema = z.discriminatedUnion('action', [
  z.object({ action: z.literal('approve'), rejection_reason: z.string().optional() }),
  z.object({
    action:           z.literal('reject'),
    rejection_reason: z.string().min(20, 'Please provide at least 20 characters explaining the rejection.'),
  }),
]);

type FormData = z.infer<typeof schema>;

// ─── Component ────────────────────────────────────────────────────────────────

interface LeaveApprovalDialogProps {
  open:          boolean;
  onOpenChange:  (open: boolean) => void;
  request:       LeaveRequestListItem | null;
  /** Balance after approval (optional — used to show post-approval remaining) */
  postApprovalBalance?: LeaveBalanceItem | null;
  onConfirm:     (action: 'approve' | 'reject', reason?: string) => Promise<void>;
  isPending?:    boolean;
}

export function LeaveApprovalDialog({
  open,
  onOpenChange,
  request,
  postApprovalBalance,
  onConfirm,
  isPending = false,
}: LeaveApprovalDialogProps) {
  const {
    register,
    handleSubmit,
    watch,
    reset,
    setValue,
    formState: { errors },
  } = useForm<FormData>({
    resolver:      zodResolver(schema),
    defaultValues: { action: 'approve', rejection_reason: '' },
  });

  const action = watch('action') as 'approve' | 'reject';

  function handleOpenChange(v: boolean) {
    if (!v) reset({ action: 'approve', rejection_reason: '' });
    onOpenChange(v);
  }

  async function onSubmit(data: FormData) {
    await onConfirm(
      data.action,
      data.action === 'reject' ? data.rejection_reason : undefined,
    );
    handleOpenChange(false);
  }

  if (!request) return null;

  const postRemaining = postApprovalBalance
    ? postApprovalBalance.remaining_days - (action === 'approve' ? request.days : 0)
    : null;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Leave Request Review</DialogTitle>
          <DialogDescription>
            Review and take action on this leave request.
          </DialogDescription>
        </DialogHeader>

        {/* Request summary */}
        <div className="rounded-lg border bg-slate-50 dark:bg-slate-800/50 p-4 space-y-3">
          {/* Employee */}
          <div className="flex items-center gap-3">
            <EmployeeAvatar name={request.employee_name} size="sm" />
            <div>
              <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
                {request.employee_name}
              </p>
              <p className="text-xs text-slate-500">{request.department_name ?? request.employee_code}</p>
            </div>
          </div>

          {/* Leave details */}
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0"
                style={{ backgroundColor: request.leave_type_color }}
              />
              {request.leave_type_name}
            </div>
            <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
              <Clock className="h-3.5 w-3.5 text-slate-400" />
              {request.days} working day{request.days !== 1 ? 's' : ''}
            </div>
            <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300 col-span-2">
              <Calendar className="h-3.5 w-3.5 text-slate-400" />
              {format(new Date(request.start_date), 'dd MMM yyyy')}
              {' → '}
              {format(new Date(request.end_date), 'dd MMM yyyy')}
            </div>
          </div>

          {/* Reason */}
          <p className="text-sm text-slate-600 dark:text-slate-400 italic border-t pt-2 dark:border-slate-700">
            "{request.reason}"
          </p>

          {/* Post-approval balance hint */}
          {postApprovalBalance && action === 'approve' && (
            <p className={cn(
              'text-xs mt-1',
              (postRemaining ?? 0) < 0 ? 'text-red-600' : 'text-slate-500',
            )}>
              After approval: {Math.max(postRemaining ?? 0, 0)} day(s) remaining
              {(postRemaining ?? 0) < 0 && ' ⚠ insufficient balance'}
            </p>
          )}
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Action toggle */}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setValue('action', 'approve')}
              className={cn(
                'flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg border text-sm font-medium transition-all',
                action === 'approve'
                  ? 'bg-green-50 border-green-400 text-green-700 dark:bg-green-950/30 dark:text-green-400'
                  : 'border-slate-200 text-slate-500 hover:border-slate-300',
              )}
            >
              <CheckCircle2 className="h-4 w-4" />
              Approve
            </button>
            <button
              type="button"
              onClick={() => setValue('action', 'reject')}
              className={cn(
                'flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg border text-sm font-medium transition-all',
                action === 'reject'
                  ? 'bg-red-50 border-red-400 text-red-700 dark:bg-red-950/30 dark:text-red-400'
                  : 'border-slate-200 text-slate-500 hover:border-slate-300',
              )}
            >
              <XCircle className="h-4 w-4" />
              Reject
            </button>
          </div>

          {/* Rejection reason */}
          {action === 'reject' && (
            <div className="space-y-1.5">
              <Label>
                Rejection reason <span className="text-red-500">*</span>
              </Label>
              <Textarea
                {...register('rejection_reason')}
                placeholder="Please explain why this request is being rejected (min. 20 characters)…"
                rows={3}
                className={errors.rejection_reason ? 'border-red-400' : ''}
              />
              {errors.rejection_reason && (
                <p className="text-xs text-red-500">{errors.rejection_reason.message}</p>
              )}
            </div>
          )}

          <DialogFooter>
            <Button
              type="button" variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isPending}
              variant={action === 'reject' ? 'destructive' : 'default'}
              className={action === 'approve' ? 'bg-green-600 hover:bg-green-700 text-white' : ''}
            >
              {isPending ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Processing…</>
              ) : action === 'approve' ? (
                <><CheckCircle2 className="mr-2 h-4 w-4" />Approve request</>
              ) : (
                <><XCircle className="mr-2 h-4 w-4" />Reject request</>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
