'use client';

import { useState }     from 'react';
import { useRouter }    from 'next/navigation';
import {
  Clock, Users, TrendingUp, AlertCircle,
  CalendarDays, BarChart3, FileCheck,
} from 'lucide-react';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton }    from '@/components/ui/skeleton';
import { Button }      from '@/components/ui/button';
import { Input }       from '@/components/ui/input';
import { Label }       from '@/components/ui/label';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';

import { CheckInCard }              from '@/components/attendance/CheckInCard';
import { LiveFeed }                 from '@/components/attendance/LiveFeed';
import { TimesheetTable }           from '@/components/attendance/TimesheetTable';
import { AttendanceMiniCalendar }   from '@/components/attendance/AttendanceMiniCalendar';

import {
  useTodayAttendance, useCheckIn, useCheckOut,
  useLiveAttendance, useLiveTodayList,
  useAttendanceSummary, useTimesheet, useExportTimesheet,
  useShifts, useAttendanceRecords, useAdjustments,
  useRequestAdjustment, useReviewAdjustment,
} from '@/hooks/useAttendance';
import { useAuthStore }   from '@/stores/authStore';
import { useDepartments } from '@/hooks/useEmployees';
import type { AttendanceRecordListItem } from '@/types/attendance';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';

// ─── Stat card ────────────────────────────────────────────────────────────────

function StatCard({
  label, value, icon: Icon, color,
}: { label: string; value: number | string; icon: React.ElementType; color: string }) {
  return (
    <Card>
      <CardContent className="p-4 flex items-center gap-4">
        <div className={cn('rounded-xl p-2.5', color)}>
          <Icon className="h-5 w-5 text-white" />
        </div>
        <div>
          <p className="text-2xl font-bold text-slate-800 dark:text-slate-100">{value}</p>
          <p className="text-xs text-slate-500">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── My Attendance tab ────────────────────────────────────────────────────────

function MyAttendanceTab() {
  const now  = new Date();
  const user = useAuthStore((s) => s.user);

  const { data: todayRecord, isLoading: todayLoading } = useTodayAttendance();
  const { data: shifts = [] } = useShifts();

  const checkInMut  = useCheckIn();
  const checkOutMut = useCheckOut();

  const empId = (user as any)?.employee_id as string | undefined;
  const { data: summary }   = useAttendanceSummary(empId, now.getMonth() + 1, now.getFullYear());
  const { data: timesheet } = useTimesheet(empId, now.getMonth() + 1, now.getFullYear());

  const employeeShift = shifts.find((s) => (user as any)?.shift_id === s.id) ?? shifts[0] ?? null;

  // Recent records (last 10)
  const { data: recentData } = useAttendanceRecords({ page: 1, page_size: 10 });

  return (
    <div className="space-y-6">
      {/* Two-col layout: check-in card + this-month stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {/* Check-in card */}
        <div className="xl:col-span-1">
          {todayLoading ? (
            <Skeleton className="h-72 rounded-2xl" />
          ) : (
            <CheckInCard
              todayRecord={todayRecord}
              shift={employeeShift}
              onCheckIn={async (geo) => {
                await checkInMut.mutateAsync({
                  source:   geo ? 'geo' : 'manual',
                  location: geo,
                });
              }}
              onCheckOut={async () => {
                await checkOutMut.mutateAsync({});
              }}
              isPending={checkInMut.isPending || checkOutMut.isPending}
            />
          )}
        </div>

        {/* Summary stat cards */}
        <div className="xl:col-span-2 grid grid-cols-2 sm:grid-cols-4 xl:grid-cols-2 gap-3 content-start">
          <StatCard label="Present days"    value={summary?.present_days    ?? '—'} icon={FileCheck}  color="bg-green-500" />
          <StatCard label="Absent days"     value={summary?.absent_days     ?? '—'} icon={AlertCircle} color="bg-red-500" />
          <StatCard label="Late arrivals"   value={summary?.late_days       ?? '—'} icon={Clock}       color="bg-yellow-500" />
          <StatCard label="Leave days"      value={summary?.leave_days      ?? '—'} icon={CalendarDays} color="bg-purple-500" />
          {summary && (
            <div className="col-span-2 sm:col-span-4 xl:col-span-2">
              <Card>
                <CardContent className="p-3">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-xs text-slate-500">Attendance rate this month</p>
                    <p className="text-sm font-bold text-slate-800 dark:text-slate-100">
                      {summary.attendance_percentage.toFixed(1)}%
                    </p>
                  </div>
                  <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-2">
                    <div
                      className={cn(
                        'h-2 rounded-full transition-all',
                        summary.attendance_percentage >= 90 ? 'bg-green-500' :
                        summary.attendance_percentage >= 75 ? 'bg-yellow-500' :
                        'bg-red-500',
                      )}
                      style={{ width: `${summary.attendance_percentage}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between mt-1 text-[10px] text-slate-400">
                    <span>{summary.total_working_hours.toFixed(1)}h worked</span>
                    <span>{summary.total_overtime_hours.toFixed(1)}h overtime</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </div>

      {/* Mini calendar */}
      {timesheet && (
        <AttendanceMiniCalendar
          rows={timesheet.rows}
          month={now.getMonth() + 1}
          year={now.getFullYear()}
          className="max-w-sm"
        />
      )}

      {/* Recent attendance table */}
      <div>
        <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide mb-3">
          Recent Attendance
        </h3>
        <div className="rounded-lg border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50 dark:bg-slate-900/50">
                <TableHead>Date</TableHead>
                <TableHead>Check-in</TableHead>
                <TableHead>Check-out</TableHead>
                <TableHead>Hours</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recentData?.results.slice(0, 10).map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="text-sm">
                    {format(new Date(r.date), 'dd MMM yyyy')}
                  </TableCell>
                  <TableCell className="text-sm tabular-nums">
                    {r.check_in ? format(new Date(r.check_in), 'HH:mm') : '—'}
                  </TableCell>
                  <TableCell className="text-sm tabular-nums">
                    {r.check_out ? format(new Date(r.check_out), 'HH:mm') : '—'}
                  </TableCell>
                  <TableCell className="text-sm tabular-nums">
                    {r.working_hours != null ? `${r.working_hours.toFixed(1)}h` : '—'}
                  </TableCell>
                  <TableCell>
                    <span className={cn(
                      'text-xs px-2 py-0.5 rounded-full border font-medium',
                      r.status === 'present'  ? 'bg-green-50 text-green-700 border-green-200' :
                      r.status === 'late'     ? 'bg-yellow-50 text-yellow-700 border-yellow-200' :
                      r.status === 'absent'   ? 'bg-red-50 text-red-700 border-red-200' :
                      'bg-slate-50 text-slate-500 border-slate-200',
                    )}>
                      {r.status.replace('_', ' ')}
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}

// ─── Live Dashboard tab ───────────────────────────────────────────────────────

function LiveDashboardTab() {
  const { feed, connected }                  = useLiveAttendance();
  const { data: liveList = [], isLoading }   = useLiveTodayList();
  const { data: departments = [] }           = useDepartments();
  const [deptFilter, setDeptFilter]          = useState('');

  const present  = liveList.filter((e) => !e.check_in_time || true).length; // all who checked in
  const late     = liveList.filter((e) => e.status === 'late').length;
  const checkedOut = liveList.filter((e) => e.action === 'check_out').length;

  const filteredList = deptFilter
    ? liveList.filter((e) => e.department_name === deptFilter)
    : liveList;

  return (
    <div className="space-y-4">
      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Checked in today"  value={liveList.length} icon={Users}      color="bg-green-500" />
        <StatCard label="Checked out"       value={checkedOut}      icon={FileCheck}  color="bg-blue-500" />
        <StatCard label="Late today"        value={late}            icon={Clock}      color="bg-yellow-500" />
        <StatCard label="WS connections"    value={connected ? '●' : '○'} icon={BarChart3} color={connected ? 'bg-green-600' : 'bg-red-500'} />
      </div>

      {/* Two-column: live feed + all-employees table */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Live feed */}
        <LiveFeed feed={feed} connected={connected} className="lg:col-span-2 h-fit" />

        {/* Today's attendance table */}
        <div className="lg:col-span-3 rounded-xl border bg-white dark:bg-slate-900 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-800/50 border-b">
            <p className="text-sm font-semibold">Today's Attendance</p>
            <Select value={deptFilter || 'all'} onValueChange={(v) => setDeptFilter(v === 'all' ? '' : v)}>
              <SelectTrigger className="h-7 text-xs w-36">
                <SelectValue placeholder="All depts" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Departments</SelectItem>
                {departments.map((d) => (
                  <SelectItem key={d.id} value={d.name}>{d.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="overflow-auto max-h-80">
            <Table>
              <TableHeader>
                <TableRow className="text-xs">
                  <TableHead>Employee</TableHead>
                  <TableHead>Check-in</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  [...Array(5)].map((_, i) => (
                    <TableRow key={i}>
                      {[...Array(3)].map((_, j) => (
                        <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                      ))}
                    </TableRow>
                  ))
                ) : filteredList.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={3} className="text-center py-8 text-slate-400 text-sm">
                      No check-ins yet today.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredList.map((e, i) => (
                    <TableRow key={`${e.employee_id}-${i}`}>
                      <TableCell>
                        <p className="text-sm font-medium">{e.employee_name}</p>
                        <p className="text-xs text-slate-400">{e.department_name}</p>
                      </TableCell>
                      <TableCell className="text-sm tabular-nums">
                        {e.check_in_time
                          ? format(new Date(e.check_in_time), 'HH:mm')
                          : '—'}
                      </TableCell>
                      <TableCell>
                        <span className={cn(
                          'text-xs px-2 py-0.5 rounded-full border font-medium',
                          e.status === 'present' ? 'bg-green-50 text-green-700 border-green-200' :
                          e.status === 'late'    ? 'bg-yellow-50 text-yellow-700 border-yellow-200' :
                          'bg-slate-50 text-slate-500 border-slate-200',
                        )}>
                          {e.status}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Timesheet tab ────────────────────────────────────────────────────────────

function TimesheetTab() {
  const now      = new Date();
  const user     = useAuthStore((s) => s.user);
  const canViewAll = useAuthStore((s) => s.hasPermission('attendance', 'view_all'));

  const [empId,  setEmpId]  = useState((user as any)?.employee_id ?? '');
  const [month,  setMonth]  = useState(now.getMonth() + 1);
  const [year,   setYear]   = useState(now.getFullYear());

  const { data, isLoading }    = useTimesheet(empId || undefined, month, year);
  const exportFn               = useExportTimesheet();
  const requestAdj             = useRequestAdjustment();

  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap gap-3 items-end">
        {canViewAll && (
          <div className="space-y-1">
            <Label className="text-xs">Employee ID</Label>
            <Input
              value={empId}
              onChange={(e) => setEmpId(e.target.value)}
              placeholder="Employee ID…"
              className="h-8 text-sm w-48"
            />
          </div>
        )}
        <div className="space-y-1">
          <Label className="text-xs">Month</Label>
          <Select
            value={String(month)}
            onValueChange={(v) => setMonth(Number(v))}
          >
            <SelectTrigger className="h-8 text-sm w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {MONTHS.map((m, i) => (
                <SelectItem key={i} value={String(i + 1)}>{m}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label className="text-xs">Year</Label>
          <Select value={String(year)} onValueChange={(v) => setYear(Number(v))}>
            <SelectTrigger className="h-8 text-sm w-24">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {[now.getFullYear() - 1, now.getFullYear(), now.getFullYear() + 1].map((y) => (
                <SelectItem key={y} value={String(y)}>{y}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <TimesheetTable
        data={data}
        isLoading={isLoading}
        canAdjust={true}
        onAdjust={(id, ci, co) => {
          requestAdj.mutate({ attendance_id: id, new_check_in: ci, new_check_out: co, reason: 'Time correction via timesheet' });
        }}
        onExport={() => {
          if (empId) exportFn(empId, month, year);
        }}
        isExporting={false}
      />
    </div>
  );
}

// ─── Adjustments tab ─────────────────────────────────────────────────────────

function AdjustmentsTab() {
  const canManage = useAuthStore((s) => s.hasPermission('attendance', 'manage'));
  const { data: myAdj    = [], isLoading: myLoading }   = useAdjustments('mine');
  const { data: pendAdj  = [], isLoading: pendLoading }  = useAdjustments('pending');
  const reviewMut = useReviewAdjustment();

  return (
    <div className="space-y-6">
      {/* My adjustment requests */}
      <div>
        <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide mb-3">
          My Requests
        </h3>
        <div className="rounded-lg border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50 dark:bg-slate-900/50 text-xs">
                <TableHead>Date</TableHead>
                <TableHead>Requested In</TableHead>
                <TableHead>Requested Out</TableHead>
                <TableHead>Reason</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {myLoading ? (
                [...Array(3)].map((_, i) => (
                  <TableRow key={i}>{[...Array(5)].map((_, j) => <TableCell key={j}><Skeleton className="h-4" /></TableCell>)}</TableRow>
                ))
              ) : myAdj.length === 0 ? (
                <TableRow><TableCell colSpan={5} className="text-center py-8 text-slate-400 text-sm">No adjustment requests.</TableCell></TableRow>
              ) : (
                myAdj.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell className="text-sm">{format(new Date(a.requested_check_in), 'dd MMM yyyy')}</TableCell>
                    <TableCell className="text-sm tabular-nums">{format(new Date(a.requested_check_in), 'HH:mm')}</TableCell>
                    <TableCell className="text-sm tabular-nums">{a.requested_check_out ? format(new Date(a.requested_check_out), 'HH:mm') : '—'}</TableCell>
                    <TableCell className="text-sm max-w-[200px] truncate text-slate-500">{a.reason}</TableCell>
                    <TableCell>
                      <span className={cn(
                        'text-xs px-2 py-0.5 rounded-full border font-medium',
                        a.status === 'approved' ? 'bg-green-50 text-green-700 border-green-200' :
                        a.status === 'rejected' ? 'bg-red-50 text-red-700 border-red-200' :
                        'bg-yellow-50 text-yellow-700 border-yellow-200',
                      )}>
                        {a.status}
                      </span>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* HR: pending approvals */}
      {canManage && (
        <div>
          <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide mb-3">
            Pending Approvals
          </h3>
          <div className="rounded-lg border overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50 dark:bg-slate-900/50 text-xs">
                  <TableHead>Employee</TableHead>
                  <TableHead>New In</TableHead>
                  <TableHead>New Out</TableHead>
                  <TableHead>Reason</TableHead>
                  <TableHead className="w-28">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pendLoading ? (
                  [...Array(3)].map((_, i) => (
                    <TableRow key={i}>{[...Array(5)].map((_, j) => <TableCell key={j}><Skeleton className="h-4" /></TableCell>)}</TableRow>
                  ))
                ) : pendAdj.length === 0 ? (
                  <TableRow><TableCell colSpan={5} className="text-center py-8 text-slate-400 text-sm">No pending adjustments.</TableCell></TableRow>
                ) : (
                  pendAdj.map((a) => (
                    <TableRow key={a.id}>
                      <TableCell className="text-sm font-medium">{a.employee_name}</TableCell>
                      <TableCell className="text-sm tabular-nums">{format(new Date(a.requested_check_in), 'dd MMM HH:mm')}</TableCell>
                      <TableCell className="text-sm tabular-nums">{a.requested_check_out ? format(new Date(a.requested_check_out), 'HH:mm') : '—'}</TableCell>
                      <TableCell className="text-sm max-w-[200px] truncate text-slate-500">{a.reason}</TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            size="sm" variant="ghost"
                            className="h-7 text-green-600 hover:text-green-700 text-xs px-2"
                            onClick={() => reviewMut.mutate({ id: a.id, action: 'approve' })}
                            disabled={reviewMut.isPending}
                          >
                            Approve
                          </Button>
                          <Button
                            size="sm" variant="ghost"
                            className="h-7 text-red-500 hover:text-red-600 text-xs px-2"
                            onClick={() => reviewMut.mutate({ id: a.id, action: 'reject' })}
                            disabled={reviewMut.isPending}
                          >
                            Reject
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AttendancePage() {
  const canViewLive = useAuthStore((s) =>
    s.hasPermission('attendance', 'view_all') || s.user?.is_superadmin
  );

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-2 px-6 py-4 border-b bg-white dark:bg-slate-950">
        <Clock className="h-5 w-5 text-hrms-600" />
        <h1 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
          Attendance & Time Tracking
        </h1>
      </div>

      <div className="flex-1 overflow-auto p-6">
        <Tabs defaultValue="my-attendance">
          <TabsList className="mb-6">
            <TabsTrigger value="my-attendance">My Attendance</TabsTrigger>
            {canViewLive && (
              <TabsTrigger value="live">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                  Live Dashboard
                </span>
              </TabsTrigger>
            )}
            <TabsTrigger value="timesheet">Timesheet</TabsTrigger>
            <TabsTrigger value="adjustments">Adjustments</TabsTrigger>
          </TabsList>

          <TabsContent value="my-attendance">
            <MyAttendanceTab />
          </TabsContent>

          {canViewLive && (
            <TabsContent value="live">
              <LiveDashboardTab />
            </TabsContent>
          )}

          <TabsContent value="timesheet">
            <TimesheetTab />
          </TabsContent>

          <TabsContent value="adjustments">
            <AdjustmentsTab />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
