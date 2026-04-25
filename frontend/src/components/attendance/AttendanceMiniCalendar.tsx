'use client';

import { useMemo }            from 'react';
import { cn }                 from '@/lib/utils';
import type { AttendanceStatus, TimesheetRow } from '@/types/attendance';

// ─── Status colours ───────────────────────────────────────────────────────────

const STATUS_DOT: Record<AttendanceStatus, string> = {
  present:  'bg-green-500',
  late:     'bg-yellow-400',
  absent:   'bg-red-500',
  half_day: 'bg-orange-400',
  on_leave: 'bg-purple-500',
  holiday:  'bg-blue-400',
  weekend:  'bg-slate-200 dark:bg-slate-700',
};

const STATUS_CELL: Record<AttendanceStatus, string> = {
  present:  'bg-green-50 dark:bg-green-950/20',
  late:     'bg-yellow-50 dark:bg-yellow-950/20',
  absent:   'bg-red-50 dark:bg-red-950/20',
  half_day: 'bg-orange-50 dark:bg-orange-950/20',
  on_leave: 'bg-purple-50 dark:bg-purple-950/20',
  holiday:  'bg-blue-50 dark:bg-blue-950/20',
  weekend:  '',
};

const STATUS_LABEL: Record<AttendanceStatus, string> = {
  present:  'Present',
  late:     'Late',
  absent:   'Absent',
  half_day: 'Half Day',
  on_leave: 'On Leave',
  holiday:  'Holiday',
  weekend:  'Weekend',
};

const DAYS = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function mondayOffset(year: number, month: number): number {
  const day = new Date(year, month - 1, 1).getDay(); // 0=Sun
  return day === 0 ? 6 : day - 1;
}

// ─── Component ────────────────────────────────────────────────────────────────

interface AttendanceMiniCalendarProps {
  rows:      TimesheetRow[];
  month:     number;
  year:      number;
  className?: string;
}

export function AttendanceMiniCalendar({
  rows,
  month,
  year,
  className,
}: AttendanceMiniCalendarProps) {
  // Build a date → row map
  const byDate = useMemo(() => {
    const map = new Map<string, TimesheetRow>();
    rows.forEach((r) => map.set(r.date, r));
    return map;
  }, [rows]);

  const daysInMonth = new Date(year, month, 0).getDate();
  const offset      = mondayOffset(year, month);
  const blanks      = Array.from({ length: offset });

  const today = new Date().toISOString().slice(0, 10);

  // Legend: unique statuses in this month
  const usedStatuses = useMemo(() => {
    const s = new Set<AttendanceStatus>();
    rows.forEach((r) => s.add(r.status));
    return Array.from(s);
  }, [rows]);

  return (
    <div className={cn('rounded-xl border bg-white dark:bg-slate-900 p-4', className)}>
      {/* Month header */}
      <p className="text-sm font-semibold text-slate-600 dark:text-slate-300 mb-3">
        {new Date(year, month - 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
      </p>

      {/* Day headers */}
      <div className="grid grid-cols-7 mb-1">
        {DAYS.map((d, i) => (
          <div
            key={i}
            className={cn(
              'text-center text-[10px] font-semibold pb-1',
              i >= 5 ? 'text-slate-400' : 'text-slate-500',
            )}
          >
            {d}
          </div>
        ))}
      </div>

      {/* Day cells */}
      <div className="grid grid-cols-7 gap-px">
        {/* Leading blanks */}
        {blanks.map((_, i) => (
          <div key={`b${i}`} className="aspect-square" />
        ))}

        {/* Day cells */}
        {Array.from({ length: daysInMonth }, (_, i) => {
          const dayNum = i + 1;
          const iso    = `${year}-${String(month).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`;
          const row    = byDate.get(iso);
          const isToday = iso === today;

          return (
            <div
              key={dayNum}
              className={cn(
                'aspect-square rounded-md flex flex-col items-center justify-center gap-0.5',
                row ? STATUS_CELL[row.status] : '',
                isToday && 'ring-2 ring-hrms-500 ring-offset-1',
              )}
              title={row ? STATUS_LABEL[row.status] : undefined}
            >
              <span className={cn(
                'text-[10px] font-medium leading-none',
                isToday ? 'text-hrms-700 dark:text-hrms-400' :
                row?.is_weekend ? 'text-slate-400' :
                'text-slate-600 dark:text-slate-300',
              )}>
                {dayNum}
              </span>
              {row && (
                <span
                  className={cn(
                    'w-1.5 h-1.5 rounded-full',
                    STATUS_DOT[row.status],
                  )}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Legend */}
      {usedStatuses.length > 0 && (
        <div className="flex flex-wrap gap-x-3 gap-y-1 mt-3 pt-3 border-t dark:border-slate-800">
          {usedStatuses.map((s) => (
            <div key={s} className="flex items-center gap-1 text-[10px] text-slate-500">
              <span className={cn('w-2 h-2 rounded-full', STATUS_DOT[s])} />
              {STATUS_LABEL[s]}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
