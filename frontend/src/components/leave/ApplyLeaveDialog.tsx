'use client';

import { useEffect, useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver }         from '@hookform/resolvers/zod';
import { z }                   from 'zod';
import { Loader2, AlertTriangle, Upload } from 'lucide-react';

import { Button }   from '@/components/ui/button';
import { Label }    from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Input }    from '@/components/ui/input';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';
import type { LeaveType, LeaveBalanceItem } from '@/types/leave';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function countWorkingDays(start: string, end: string, holidays: string[]): number {
  if (!start || !end) return 0;
  const s = new Date(start);
  const e = new Date(end);
  if (e < s) return 0;
  const holidaySet = new Set(holidays);
  let count = 0;
  const cur = new Date(s);
  while (cur <= e) {
    const day = cur.getDay();
    const iso = cur.toISOString().slice(0, 10);
    if (day !== 0 && day !== 6 && !holidaySet.has(iso)) count++;
    cur.setDate(cur.getDate() + 1);
  }
  return count;
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

// ─── Schema ───────────────────────────────────────────────────────────────────

const schema = z.object({
  leave_type_id: z.string().min(1, 'Please select a leave type'),
  start_date:    z.string().min(1, 'Start date is required'),
  end_date:      z.string().min(1, 'End date is required'),
  reason:        z.string().min(10, 'Reason must be at least 10 characters'),
  document_url:  z.string().optional(),
}).superRefine((data, ctx) => {
  if (data.start_date && data.end_date && data.end_date < data.start_date) {
    ctx.addIssue({
      code:    z.ZodIssueCode.custom,
      path:    ['end_date'],
      message: 'End date must be on or after start date',
    });
  }
});

type FormData = z.infer<typeof schema>;

// ─── Component ────────────────────────────────────────────────────────────────

interface ApplyLeaveDialogProps {
  open:          boolean;
  onOpenChange:  (open: boolean) => void;
  leaveTypes:    LeaveType[];
  balances:      LeaveBalanceItem[];
  /** ISO date strings of public holidays — used for client-side working day count */
  publicHolidays?: string[];
  /** Other team members on leave for conflict warning */
  teamOnLeave?:    { name: string; start_date: string; end_date: string }[];
  onConfirm:     (data: FormData, days: number) => Promise<void>;
  isPending?:    boolean;
}

export function ApplyLeaveDialog({
  open,
  onOpenChange,
  leaveTypes,
  balances,
  publicHolidays = [],
  teamOnLeave    = [],
  onConfirm,
  isPending = false,
}: ApplyLeaveDialogProps) {
  const [workingDays, setWorkingDays] = useState(0);
  const [conflicts,   setConflicts]   = useState<typeof teamOnLeave>([]);

  const {
    register,
    handleSubmit,
    control,
    watch,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    resolver:      zodResolver(schema),
    defaultValues: { start_date: today(), end_date: today() },
  });

  const selectedTypeId = watch('leave_type_id');
  const startDate      = watch('start_date');
  const endDate        = watch('end_date');

  const selectedType    = leaveTypes.find((t) => t.id === selectedTypeId);
  const selectedBalance = balances.find((b) => b.leave_type_id === selectedTypeId);
  const isInsufficient  = selectedBalance
    ? workingDays > selectedBalance.remaining_days
    : false;

  // Recalculate working days when dates change
  useEffect(() => {
    setWorkingDays(countWorkingDays(startDate, endDate, publicHolidays));
  }, [startDate, endDate, publicHolidays]);

  // Conflict detection
  useEffect(() => {
    if (!startDate || !endDate) { setConflicts([]); return; }
    const s = new Date(startDate);
    const e = new Date(endDate);
    const found = teamOnLeave.filter((m) => {
      const ms = new Date(m.start_date);
      const me = new Date(m.end_date);
      return ms <= e && me >= s;
    });
    setConflicts(found);
  }, [startDate, endDate, teamOnLeave]);

  function handleOpenChange(v: boolean) {
    if (!v) { reset(); setWorkingDays(0); setConflicts([]); }
    onOpenChange(v);
  }

  async function onSubmit(data: FormData) {
    await onConfirm(data, workingDays);
    handleOpenChange(false);
  }

  // Sort leave types: active first, with balance info
  const typeOptions = leaveTypes
    .filter((t) => t.is_active)
    .map((t) => {
      const bal = balances.find((b) => b.leave_type_id === t.id);
      return { ...t, remaining: bal?.remaining_days ?? t.days_allowed };
    });

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Apply for Leave</DialogTitle>
          <DialogDescription>
            Submit a new leave request. Working days are calculated automatically.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-1">
          {/* Leave type */}
          <div className="space-y-1.5">
            <Label>Leave type <span className="text-red-500">*</span></Label>
            <Controller
              control={control}
              name="leave_type_id"
              render={({ field }) => (
                <Select onValueChange={field.onChange} value={field.value ?? ''}>
                  <SelectTrigger className={errors.leave_type_id ? 'border-red-400' : ''}>
                    <SelectValue placeholder="Select leave type…" />
                  </SelectTrigger>
                  <SelectContent>
                    {typeOptions.map((t) => (
                      <SelectItem
                        key={t.id}
                        value={t.id}
                        disabled={t.remaining <= 0}
                      >
                        <div className="flex items-center justify-between gap-4 w-full">
                          <div className="flex items-center gap-2">
                            <span
                              className="w-2.5 h-2.5 rounded-full shrink-0"
                              style={{ backgroundColor: t.color }}
                            />
                            {t.name}
                          </div>
                          <span className={cn(
                            'text-xs',
                            t.remaining <= 0 ? 'text-red-500' :
                            t.remaining <= 3 ? 'text-yellow-600' :
                            'text-slate-400',
                          )}>
                            {t.remaining}/{t.days_allowed}d
                          </span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {errors.leave_type_id && (
              <p className="text-xs text-red-500">{errors.leave_type_id.message}</p>
            )}
          </div>

          {/* Date range */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Start date <span className="text-red-500">*</span></Label>
              <Input
                type="date"
                {...register('start_date')}
                min={today()}
                className={errors.start_date ? 'border-red-400' : ''}
              />
              {errors.start_date && (
                <p className="text-xs text-red-500">{errors.start_date.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label>End date <span className="text-red-500">*</span></Label>
              <Input
                type="date"
                {...register('end_date')}
                min={startDate || today()}
                className={errors.end_date ? 'border-red-400' : ''}
              />
              {errors.end_date && (
                <p className="text-xs text-red-500">{errors.end_date.message}</p>
              )}
            </div>
          </div>

          {/* Working days summary */}
          {workingDays > 0 && (
            <div className={cn(
              'flex items-center justify-between rounded-lg px-3 py-2 text-sm',
              isInsufficient
                ? 'bg-red-50 border border-red-200 text-red-700 dark:bg-red-950/20 dark:border-red-900'
                : 'bg-hrms-50 border border-hrms-200 text-hrms-700 dark:bg-hrms-950/20 dark:border-hrms-900',
            )}>
              <span>Working days requested</span>
              <strong>{workingDays}</strong>
            </div>
          )}

          {/* Insufficient balance warning */}
          {isInsufficient && selectedBalance && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-red-50 border border-red-200 dark:bg-red-950/20 dark:border-red-900">
              <AlertTriangle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
              <p className="text-sm text-red-700 dark:text-red-400">
                Insufficient balance. You have {selectedBalance.remaining_days} day(s) remaining
                but requested {workingDays}.
              </p>
            </div>
          )}

          {/* Team conflict warning */}
          {conflicts.length > 0 && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-yellow-50 border border-yellow-200 dark:bg-yellow-950/20 dark:border-yellow-800">
              <AlertTriangle className="h-4 w-4 text-yellow-600 shrink-0 mt-0.5" />
              <div className="text-sm text-yellow-700 dark:text-yellow-400">
                <p className="font-medium mb-1">Team members also on leave:</p>
                <ul className="text-xs space-y-0.5">
                  {conflicts.slice(0, 3).map((c, i) => (
                    <li key={i}>{c.name} ({c.start_date} → {c.end_date})</li>
                  ))}
                  {conflicts.length > 3 && <li>and {conflicts.length - 3} more…</li>}
                </ul>
              </div>
            </div>
          )}

          {/* Reason */}
          <div className="space-y-1.5">
            <Label>Reason <span className="text-red-500">*</span></Label>
            <Textarea
              {...register('reason')}
              placeholder="Please describe the reason for your leave request…"
              rows={3}
              className={errors.reason ? 'border-red-400' : ''}
            />
            {errors.reason && (
              <p className="text-xs text-red-500">{errors.reason.message}</p>
            )}
          </div>

          {/* Document upload — only if leave type requires it */}
          {selectedType?.requires_document && (
            <div className="space-y-1.5">
              <Label className="flex items-center gap-1">
                <Upload className="h-3.5 w-3.5" />
                Supporting document <span className="text-red-500">*</span>
              </Label>
              <Input
                type="url"
                {...register('document_url')}
                placeholder="Paste document URL or upload link…"
                className="text-sm"
              />
              <p className="text-xs text-slate-400">
                Required for {selectedType.name}. Provide a URL to the uploaded file.
              </p>
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
              disabled={isPending || isInsufficient || workingDays === 0}
              className="bg-hrms-600 hover:bg-hrms-700 text-white"
            >
              {isPending ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Submitting…</>
              ) : (
                `Submit (${workingDays} day${workingDays !== 1 ? 's' : ''})`
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
