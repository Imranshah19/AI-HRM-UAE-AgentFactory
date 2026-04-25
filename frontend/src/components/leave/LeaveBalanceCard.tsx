'use client';

import { cn } from '@/lib/utils';
import type { LeaveBalanceItem } from '@/types/leave';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function pct(used: number, total: number): number {
  if (total === 0) return 0;
  return Math.min(Math.round((used / total) * 100), 100);
}

function colorClass(remaining: number, total: number): string {
  if (total === 0) return 'text-slate-400';
  const ratio = remaining / total;
  if (ratio > 0.5)  return 'text-green-600';
  if (ratio > 0.2)  return 'text-yellow-600';
  return 'text-red-600';
}

function bgClass(remaining: number, total: number): string {
  if (total === 0) return 'bg-slate-200';
  const ratio = remaining / total;
  if (ratio > 0.5)  return 'bg-green-500';
  if (ratio > 0.2)  return 'bg-yellow-500';
  return 'bg-red-500';
}

function trackClass(remaining: number, total: number): string {
  if (total === 0) return 'bg-slate-100';
  const ratio = remaining / total;
  if (ratio > 0.5)  return 'bg-green-100 dark:bg-green-950/30';
  if (ratio > 0.2)  return 'bg-yellow-100 dark:bg-yellow-950/30';
  return 'bg-red-100 dark:bg-red-950/30';
}

// ─── Component ────────────────────────────────────────────────────────────────

interface LeaveBalanceCardProps {
  balance:   LeaveBalanceItem;
  className?: string;
  onClick?:  () => void;
}

export function LeaveBalanceCard({ balance, className, onClick }: LeaveBalanceCardProps) {
  const used      = pct(balance.used_days, balance.total_days);
  const remaining = balance.remaining_days;
  const total     = balance.total_days;

  return (
    <div
      onClick={onClick}
      className={cn(
        'rounded-xl border bg-white dark:bg-slate-900 p-4 flex flex-col gap-3',
        onClick && 'cursor-pointer hover:shadow-md transition-shadow',
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          {/* Color dot using leave type's color */}
          <span
            className="w-2.5 h-2.5 rounded-full shrink-0"
            style={{ backgroundColor: balance.leave_type_color }}
          />
          <span className="text-sm font-medium text-slate-700 dark:text-slate-200 truncate">
            {balance.leave_type_name}
          </span>
        </div>
        <span className={cn(
          'text-xs font-semibold shrink-0',
          balance.is_paid ? 'text-green-600' : 'text-slate-400',
        )}>
          {balance.is_paid ? 'Paid' : 'Unpaid'}
        </span>
      </div>

      {/* Days display */}
      <div className="flex items-end justify-between">
        <div>
          <span className={cn('text-3xl font-bold tabular-nums', colorClass(remaining, total))}>
            {remaining}
          </span>
          <span className="text-xs text-slate-400 ml-1">/ {total} days</span>
        </div>
        <span className="text-xs text-slate-500">{balance.used_days} used</span>
      </div>

      {/* Progress bar */}
      <div className={cn('w-full rounded-full h-2 overflow-hidden', trackClass(remaining, total))}>
        <div
          className={cn('h-2 rounded-full transition-all', bgClass(remaining, total))}
          style={{ width: `${used}%` }}
        />
      </div>

      {/* Carry forward note */}
      {balance.carried_forward > 0 && (
        <p className="text-[11px] text-slate-400">
          Includes {balance.carried_forward} day(s) carried forward
        </p>
      )}
    </div>
  );
}
