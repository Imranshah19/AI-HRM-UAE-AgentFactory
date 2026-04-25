'use client';

import { useState }  from 'react';
import { format }    from 'date-fns';
import { Download, Edit2, Check, X } from 'lucide-react';

import { Button }    from '@/components/ui/button';
import { Input }     from '@/components/ui/input';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { Skeleton }  from '@/components/ui/skeleton';
import { cn }        from '@/lib/utils';
import type { TimesheetRow, TimesheetResponse } from '@/types/attendance';

// ─── Row colour map ───────────────────────────────────────────────────────────

function rowClass(row: TimesheetRow): string {
  if (row.is_weekend) return 'bg-slate-50/60 dark:bg-slate-900/30 text-slate-400';
  if (row.is_holiday) return 'bg-blue-50/60 dark:bg-blue-950/10';
  switch (row.status) {
    case 'absent':   return 'bg-red-50/50 dark:bg-red-950/10';
    case 'late':     return 'bg-yellow-50/50 dark:bg-yellow-950/10';
    case 'half_day': return 'bg-orange-50/50 dark:bg-orange-950/10';
    case 'on_leave': return 'bg-purple-50/50 dark:bg-purple-950/10';
    default:         return '';
  }
}

// ─── Status badge ─────────────────────────────────────────────────────────────

const STATUS_STYLE: Record<string, string> = {
  present:  'text-green-700 bg-green-100 border-green-200',
  late:     'text-yellow-700 bg-yellow-100 border-yellow-200',
  absent:   'text-red-700 bg-red-100 border-red-200',
  half_day: 'text-orange-700 bg-orange-100 border-orange-200',
  on_leave: 'text-purple-700 bg-purple-100 border-purple-200',
  holiday:  'text-blue-700 bg-blue-100 border-blue-200',
  weekend:  'text-slate-500 bg-slate-100 border-slate-200',
};

function StatusBadge({ status }: { status: string }) {
  const label = status.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <span className={cn(
      'inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border',
      STATUS_STYLE[status] ?? 'text-slate-500 bg-slate-100 border-slate-200',
    )}>
      {label}
    </span>
  );
}

// ─── Inline edit row ──────────────────────────────────────────────────────────

function EditableRow({
  row,
  onSave,
}: {
  row:    TimesheetRow;
  onSave: (id: string, checkIn: string, checkOut: string) => void;
}) {
  const [editing,  setEditing]  = useState(false);
  const [newIn,    setNewIn]    = useState(row.check_in  ? format(new Date(row.check_in),  "HH:mm") : '');
  const [newOut,   setNewOut]   = useState(row.check_out ? format(new Date(row.check_out), "HH:mm") : '');

  if (!editing || !row.attendance_id) {
    return (
      <Button
        variant="ghost" size="icon" className="h-6 w-6 ml-1 opacity-40 hover:opacity-100"
        onClick={() => row.attendance_id && setEditing(true)}
        disabled={!row.attendance_id}
        title="Request adjustment"
      >
        <Edit2 className="h-3 w-3" />
      </Button>
    );
  }

  return (
    <div className="flex items-center gap-1">
      <Input
        type="time" value={newIn}
        onChange={(e) => setNewIn(e.target.value)}
        className="h-6 w-20 text-xs px-1"
      />
      <span className="text-slate-300">→</span>
      <Input
        type="time" value={newOut}
        onChange={(e) => setNewOut(e.target.value)}
        className="h-6 w-20 text-xs px-1"
      />
      <Button
        variant="ghost" size="icon" className="h-6 w-6 text-green-600"
        onClick={() => {
          if (row.attendance_id) {
            const dateStr = row.date;
            onSave(
              row.attendance_id,
              newIn  ? `${dateStr}T${newIn}:00` : '',
              newOut ? `${dateStr}T${newOut}:00` : '',
            );
          }
          setEditing(false);
        }}
      >
        <Check className="h-3 w-3" />
      </Button>
      <Button
        variant="ghost" size="icon" className="h-6 w-6 text-red-500"
        onClick={() => setEditing(false)}
      >
        <X className="h-3 w-3" />
      </Button>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

interface TimesheetTableProps {
  data:        TimesheetResponse | null | undefined;
  isLoading?:  boolean;
  canAdjust?:  boolean;
  onAdjust?:   (attendanceId: string, newCheckIn: string, newCheckOut: string) => void;
  onExport?:   () => void;
  isExporting?: boolean;
}

export function TimesheetTable({
  data,
  isLoading  = false,
  canAdjust  = false,
  onAdjust,
  onExport,
  isExporting = false,
}: TimesheetTableProps) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {[...Array(8)].map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
      </div>
    );
  }

  if (!data) return null;

  const fmtTime = (dt: string | null | undefined) =>
    dt ? format(new Date(dt), 'HH:mm') : '—';

  const fmtHours = (h: number | null | undefined) =>
    h != null ? `${h.toFixed(1)}h` : '—';

  return (
    <div className="rounded-lg border overflow-hidden">
      {/* Table header with export */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-50 dark:bg-slate-800/50 border-b">
        <p className="text-sm font-medium text-slate-600 dark:text-slate-300">
          {data.employee_name} · {new Date(data.year, data.month - 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
        </p>
        {onExport && (
          <Button
            variant="outline" size="sm" className="h-7 text-xs gap-1.5"
            onClick={onExport}
            disabled={isExporting}
          >
            <Download className="h-3 w-3" />
            {isExporting ? 'Exporting…' : 'Export Excel'}
          </Button>
        )}
      </div>

      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-slate-50/80 dark:bg-slate-900/50 text-xs">
              <TableHead className="w-24">Date</TableHead>
              <TableHead className="w-20">Day</TableHead>
              <TableHead>Check-in</TableHead>
              <TableHead>Check-out</TableHead>
              <TableHead>Hours</TableHead>
              <TableHead>OT</TableHead>
              <TableHead>Status</TableHead>
              {canAdjust && <TableHead className="w-8" />}
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.rows.map((row) => (
              <TableRow
                key={row.date}
                className={cn('text-sm', rowClass(row))}
              >
                <TableCell className="font-mono text-xs py-2">
                  {format(new Date(row.date), 'dd MMM')}
                </TableCell>
                <TableCell className={cn('text-xs py-2', row.is_weekend && 'text-slate-400')}>
                  {row.day_name.slice(0, 3)}
                </TableCell>
                <TableCell className="tabular-nums py-2 text-xs">
                  {row.is_weekend || row.is_holiday ? (
                    <span className="text-slate-400">
                      {row.is_holiday ? row.holiday_name : '—'}
                    </span>
                  ) : fmtTime(row.check_in)}
                </TableCell>
                <TableCell className="tabular-nums py-2 text-xs">
                  {!row.is_weekend && !row.is_holiday ? fmtTime(row.check_out) : null}
                </TableCell>
                <TableCell className="tabular-nums py-2 text-xs font-medium">
                  {fmtHours(row.working_hours)}
                </TableCell>
                <TableCell className={cn('tabular-nums py-2 text-xs', (row.overtime_hours ?? 0) > 0 && 'text-orange-600 font-medium')}>
                  {(row.overtime_hours ?? 0) > 0 ? `+${fmtHours(row.overtime_hours)}` : '—'}
                </TableCell>
                <TableCell className="py-2">
                  <StatusBadge status={row.status} />
                </TableCell>
                {canAdjust && (
                  <TableCell className="py-2">
                    {!row.is_weekend && !row.is_holiday && (
                      <EditableRow
                        row={row}
                        onSave={(id, ci, co) => onAdjust?.(id, ci, co)}
                      />
                    )}
                  </TableCell>
                )}
              </TableRow>
            ))}

            {/* Totals row */}
            <TableRow className="bg-slate-100/70 dark:bg-slate-800/50 font-semibold text-sm border-t-2">
              <TableCell colSpan={2} className="py-2.5 text-xs text-slate-600">Totals</TableCell>
              <TableCell className="py-2.5 text-xs text-slate-500">
                {data.total_present_days} days present
              </TableCell>
              <TableCell />
              <TableCell className="py-2.5 text-xs tabular-nums">
                {data.total_working_hours.toFixed(1)}h
              </TableCell>
              <TableCell className={cn('py-2.5 text-xs tabular-nums', data.total_overtime_hours > 0 && 'text-orange-600')}>
                {data.total_overtime_hours > 0 ? `+${data.total_overtime_hours.toFixed(1)}h` : '—'}
              </TableCell>
              <TableCell />
              {canAdjust && <TableCell />}
            </TableRow>
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
