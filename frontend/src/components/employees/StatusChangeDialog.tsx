'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { AlertTriangle, Loader2 } from 'lucide-react';

import { Button }     from '@/components/ui/button';
import { Label }      from '@/components/ui/label';
import { Textarea }   from '@/components/ui/textarea';
import {
  Dialog, DialogContent, DialogDescription,
  DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { EmployeeStatusBadge } from './EmployeeStatusBadge';
import type { EmployeeStatus }  from '@/types/employee';

// ─── Schema ───────────────────────────────────────────────────────────────────

const REQUIRES_REASON: EmployeeStatus[] = ['terminated', 'resigned', 'suspended'];

const schema = z.object({
  employment_status: z.string().min(1, 'Please select a status'),
  reason:            z.string().optional(),
}).superRefine((data, ctx) => {
  if (REQUIRES_REASON.includes(data.employment_status as EmployeeStatus) && !data.reason?.trim()) {
    ctx.addIssue({
      code:    z.ZodIssueCode.custom,
      path:    ['reason'],
      message: 'A reason is required for this status change.',
    });
  }
});

type FormData = z.infer<typeof schema>;

// ─── Status options ───────────────────────────────────────────────────────────

const STATUS_OPTIONS: { value: EmployeeStatus; label: string }[] = [
  { value: 'active',     label: 'Active' },
  { value: 'inactive',   label: 'Inactive' },
  { value: 'on_leave',   label: 'On Leave' },
  { value: 'suspended',  label: 'Suspended' },
  { value: 'resigned',   label: 'Resigned' },
  { value: 'terminated', label: 'Terminated' },
];

const IRREVERSIBLE: EmployeeStatus[] = ['terminated', 'resigned'];

// ─── Component ────────────────────────────────────────────────────────────────

interface StatusChangeDialogProps {
  open:            boolean;
  onOpenChange:    (open: boolean) => void;
  currentStatus:   EmployeeStatus;
  employeeName:    string;
  onConfirm:       (status: EmployeeStatus, reason: string | undefined) => Promise<void>;
  isPending?:      boolean;
}

export function StatusChangeDialog({
  open,
  onOpenChange,
  currentStatus,
  employeeName,
  onConfirm,
  isPending = false,
}: StatusChangeDialogProps) {
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { employment_status: currentStatus },
  });

  const selectedStatus = watch('employment_status') as EmployeeStatus;
  const isIrreversible = IRREVERSIBLE.includes(selectedStatus);
  const needsReason    = REQUIRES_REASON.includes(selectedStatus);

  // Reset form when dialog opens
  useEffect(() => {
    if (open) reset({ employment_status: currentStatus, reason: '' });
  }, [open, currentStatus, reset]);

  async function onSubmit(data: FormData) {
    await onConfirm(
      data.employment_status as EmployeeStatus,
      data.reason?.trim() || undefined,
    );
    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Change Employment Status</DialogTitle>
          <DialogDescription>
            Update the status for <strong>{employeeName}</strong>.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-2">
          {/* Current status */}
          <div className="flex items-center gap-2 p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
            <span className="text-sm text-slate-500">Current:</span>
            <EmployeeStatusBadge status={currentStatus} />
          </div>

          {/* New status selector */}
          <div className="space-y-1.5">
            <Label>New status</Label>
            <Select
              onValueChange={(v) => setValue('employment_status', v, { shouldValidate: true })}
              defaultValue={currentStatus}
            >
              <SelectTrigger className={errors.employment_status ? 'border-red-400' : ''}>
                <SelectValue placeholder="Select status…" />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.filter((o) => o.value !== currentStatus).map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    <EmployeeStatusBadge status={opt.value} size="sm" />
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.employment_status && (
              <p className="text-xs text-red-500">{errors.employment_status.message}</p>
            )}
          </div>

          {/* Reason textarea */}
          {selectedStatus !== currentStatus && (
            <div className="space-y-1.5">
              <Label>
                Reason{needsReason && <span className="text-red-500 ml-0.5">*</span>}
              </Label>
              <Textarea
                {...register('reason')}
                placeholder={
                  needsReason
                    ? 'Please provide the reason for this status change…'
                    : 'Optional notes…'
                }
                rows={3}
                className={errors.reason ? 'border-red-400' : ''}
              />
              {errors.reason && (
                <p className="text-xs text-red-500">{errors.reason.message}</p>
              )}
            </div>
          )}

          {/* Irreversible warning */}
          {isIrreversible && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-red-50 border border-red-200 dark:bg-red-950/20 dark:border-red-900">
              <AlertTriangle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
              <p className="text-sm text-red-700 dark:text-red-400">
                <strong>Warning:</strong> This action{' '}
                {selectedStatus === 'terminated' ? 'terminates' : 'records a resignation for'}{' '}
                the employee and deactivates their system account. This is difficult to reverse.
              </p>
            </div>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isPending || selectedStatus === currentStatus}
              variant={isIrreversible ? 'destructive' : 'default'}
              className={!isIrreversible ? 'bg-hrms-600 hover:bg-hrms-700 text-white' : ''}
            >
              {isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Updating…
                </>
              ) : (
                'Confirm change'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
