'use client';

import { useState, useMemo } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import {
  Popover, PopoverContent, PopoverTrigger,
} from '@/components/ui/popover';
import { Button }         from '@/components/ui/button';
import { EmployeeAvatar } from '@/components/employees/EmployeeAvatar';
import { cn }             from '@/lib/utils';
import type { LeaveCalendarEntry } from '@/types/leave';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const DAYS   = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const MONTHS = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December',
];

function getDaysInMonth(year: number, month: number): Date[] {
  const days: Date[] = [];
  const first = new Date(year, month - 1, 1);
  const last  = new Date(year, month, 0);
  for (let d = 1; d <= last.getDate(); d++) {
    days.push(new Date(year, month - 1, d));
  }
  return days;
}

// Monday-based offset (0=Mon ... 6=Sun)
function startOffset(year: number, month: number): number {
  const day = new Date(year, month - 1, 1).getDay(); // 0=Sun
  return day === 0 ? 6 : day - 1;
}

function toKey(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function isToday(d: Date): boolean {
  const t = new Date();
  return d.getFullYear() === t.getFullYear() &&
         d.getMonth() === t.getMonth() &&
         d.getDate() === t.getDate();
}

function isWeekend(d: Date): boolean {
  return d.getDay() === 0 || d.getDay() === 6;
}

// ─── Legend ───────────────────────────────────────────────────────────────────

function Legend({ entries }: { entries: LeaveCalendarEntry[] }) {
  const types = useMemo(() => {
    const map = new Map<string, { name: string; color: string }>();
    entries.forEach((e) => map.set(e.leave_type_id, {
      name:  e.leave_type_name,
      color: e.leave_type_color,
    }));
    return Array.from(map.values());
  }, [entries]);

  if (types.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-3 mt-3">
      {types.map((t) => (
        <div key={t.name} className="flex items-center gap-1.5 text-xs text-slate-500">
          <span className="w-3 h-3 rounded-full" style={{ backgroundColor: t.color }} />
          {t.name}
        </div>
      ))}
    </div>
  );
}

// ─── Day cell ─────────────────────────────────────────────────────────────────

const MAX_AVATARS = 3;

function DayCell({
  date,
  entries,
}: {
  date:    Date;
  entries: LeaveCalendarEntry[];
}) {
  const today   = isToday(date);
  const weekend = isWeekend(date);
  const visible = entries.slice(0, MAX_AVATARS);
  const overflow = entries.length - MAX_AVATARS;

  const cell = (
    <div
      className={cn(
        'min-h-[80px] p-1.5 border-b border-r border-slate-100 dark:border-slate-800 flex flex-col',
        weekend && 'bg-slate-50/60 dark:bg-slate-900/30',
        today   && 'bg-hrms-50/40 dark:bg-hrms-950/20',
      )}
    >
      {/* Date number */}
      <span
        className={cn(
          'text-xs font-medium w-6 h-6 flex items-center justify-center rounded-full self-start mb-1',
          today
            ? 'bg-hrms-600 text-white'
            : weekend
            ? 'text-slate-400'
            : 'text-slate-600 dark:text-slate-300',
        )}
      >
        {date.getDate()}
      </span>

      {/* Avatars */}
      {entries.length > 0 && (
        <div className="flex flex-wrap gap-0.5 mt-auto">
          {visible.map((e) => (
            <div
              key={`${e.employee_id}-${e.date}`}
              style={{ borderColor: e.leave_type_color }}
              className="rounded-full border-2"
            >
              <EmployeeAvatar
                name={e.employee_name}
                photoUrl={e.photo_url}
                size="xs"
              />
            </div>
          ))}
          {overflow > 0 && (
            <span className="text-[10px] text-slate-400 font-medium self-center ml-0.5">
              +{overflow}
            </span>
          )}
        </div>
      )}
    </div>
  );

  if (entries.length === 0) return cell;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button type="button" className="w-full text-left">{cell}</button>
      </PopoverTrigger>
      <PopoverContent className="w-64 p-3" side="top">
        <p className="text-xs font-semibold text-slate-500 mb-2">
          {date.toLocaleDateString('en-PK', { weekday: 'long', day: 'numeric', month: 'long' })}
        </p>
        <div className="space-y-2 max-h-48 overflow-auto">
          {entries.map((e) => (
            <div key={`${e.employee_id}-${e.date}`} className="flex items-center gap-2">
              <EmployeeAvatar name={e.employee_name} photoUrl={e.photo_url} size="xs" />
              <div className="min-w-0">
                <p className="text-xs font-medium text-slate-700 dark:text-slate-200 truncate">
                  {e.employee_name}
                </p>
                <p className="text-[10px] text-slate-400 flex items-center gap-1">
                  <span
                    className="w-2 h-2 rounded-full inline-block"
                    style={{ backgroundColor: e.leave_type_color }}
                  />
                  {e.leave_type_name}
                </p>
              </div>
            </div>
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

interface LeaveCalendarProps {
  entries:    LeaveCalendarEntry[];
  month:      number;
  year:       number;
  onNavigate: (month: number, year: number) => void;
  className?: string;
}

export function LeaveCalendar({
  entries,
  month,
  year,
  onNavigate,
  className,
}: LeaveCalendarProps) {
  // Group entries by ISO date
  const byDate = useMemo(() => {
    const map = new Map<string, LeaveCalendarEntry[]>();
    entries.forEach((e) => {
      const key = e.date;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(e);
    });
    return map;
  }, [entries]);

  const days   = getDaysInMonth(year, month);
  const offset = startOffset(year, month);
  const blanks = Array.from({ length: offset });

  function prev() {
    if (month === 1) onNavigate(12, year - 1);
    else             onNavigate(month - 1, year);
  }

  function next() {
    if (month === 12) onNavigate(1, year + 1);
    else              onNavigate(month + 1, year);
  }

  return (
    <div className={cn('flex flex-col', className)}>
      {/* Navigation */}
      <div className="flex items-center justify-between mb-4">
        <Button variant="outline" size="icon" className="h-8 w-8" onClick={prev}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <h2 className="text-base font-semibold text-slate-700 dark:text-slate-200">
          {MONTHS[month - 1]} {year}
        </h2>
        <Button variant="outline" size="icon" className="h-8 w-8" onClick={next}>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* Grid */}
      <div className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
        {/* Header row */}
        <div className="grid grid-cols-7 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700">
          {DAYS.map((d) => (
            <div
              key={d}
              className={cn(
                'text-center text-xs font-semibold py-2 text-slate-500',
                (d === 'Sat' || d === 'Sun') && 'text-slate-400',
              )}
            >
              {d}
            </div>
          ))}
        </div>

        {/* Day cells */}
        <div className="grid grid-cols-7">
          {/* Leading blanks */}
          {blanks.map((_, i) => (
            <div key={`blank-${i}`} className="min-h-[80px] border-b border-r border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-900/10" />
          ))}

          {/* Day cells */}
          {days.map((day) => (
            <DayCell
              key={toKey(day)}
              date={day}
              entries={byDate.get(toKey(day)) ?? []}
            />
          ))}

          {/* Trailing blanks to complete the last week row */}
          {Array.from({ length: (7 - ((offset + days.length) % 7)) % 7 }).map((_, i) => (
            <div key={`trail-${i}`} className="min-h-[80px] border-b border-r border-slate-100 dark:border-slate-800 bg-slate-50/30" />
          ))}
        </div>
      </div>

      {/* Legend */}
      <Legend entries={entries} />
    </div>
  );
}
