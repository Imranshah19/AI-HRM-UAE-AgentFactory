'use client';

import { useState, useMemo } from 'react';
import { format }            from 'date-fns';
import {
  CalendarDays, Plus, CheckCircle2, XCircle, Trash2,
  Settings, Filter, Building2,
} from 'lucide-react';

import { Button }    from '@/components/ui/button';
import { Badge }     from '@/components/ui/badge';
import { Skeleton }  from '@/components/ui/skeleton';
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from '@/components/ui/tabs';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Card, CardContent, CardHeader, CardTitle,
} from '@/components/ui/card';
import { Input }     from '@/components/ui/input';
import { Label }     from '@/components/ui/label';

import { LeaveBalanceCard }    from '@/components/leave/LeaveBalanceCard';
import { LeaveCalendar }       from '@/components/leave/LeaveCalendar';
import { ApplyLeaveDialog }    from '@/components/leave/ApplyLeaveDialog';
import { LeaveApprovalDialog } from '@/components/leave/LeaveApprovalDialog';

import {
  useLeaveTypes, useLeaveRequests, useMyLeaveBalance, useLeaveCalendar,
  useApplyLeave, useCancelLeave, useApproveLeave,
  useCreateLeaveType, useUpdateLeaveType, useDeleteLeaveType,
  usePublicHolidays, useCreatePublicHoliday, useDeletePublicHoliday,
  useLeaveBalance,
} from '@/hooks/useLeave';
import { useDepartments } from '@/hooks/useEmployees';
import { useAuthStore }   from '@/stores/authStore';
import type { LeaveRequestListItem, LeaveStatus, LeaveTypeCreate } from '@/types/leave';

// ─── Status badge ─────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<LeaveStatus, string> = {
  pending:   'bg-yellow-100 text-yellow-800 border-yellow-200',
  approved:  'bg-green-100 text-green-700 border-green-200',
  rejected:  'bg-red-100 text-red-700 border-red-200',
  cancelled: 'bg-slate-100 text-slate-500 border-slate-200',
};

function StatusBadge({ status }: { status: LeaveStatus }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full border ${STATUS_STYLES[status]}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

// ─── My Leaves tab ────────────────────────────────────────────────────────────

function MyLeavesTab() {
  const [applyOpen, setApplyOpen] = useState(false);
  const [page, setPage]           = useState(1);

  const { data: balance, isLoading: balanceLoading } = useMyLeaveBalance();
  const { data: reqData, isLoading: reqLoading }     = useLeaveRequests({ page, page_size: 10 });
  const { data: leaveTypes = [] }                    = useLeaveTypes();
  const { data: holidays   = [] }                    = usePublicHolidays(new Date().getFullYear());

  const cancelMutation = useCancelLeave();
  const applyMutation  = useApplyLeave();

  const holidayDates = holidays.map((h) => h.date);

  return (
    <div className="space-y-6">
      {/* Balance cards */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide">
            Leave Balance
          </h2>
          <Button
            size="sm"
            className="bg-hrms-600 hover:bg-hrms-700 text-white gap-1.5"
            onClick={() => setApplyOpen(true)}
          >
            <Plus className="h-4 w-4" />
            Apply for Leave
          </Button>
        </div>

        {balanceLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
            {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-32 rounded-xl" />)}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
            {balance?.balances.map((b) => (
              <LeaveBalanceCard key={b.leave_type_id} balance={b} />
            ))}
          </div>
        )}
      </div>

      {/* My requests */}
      <div>
        <h2 className="text-sm font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide mb-3">
          My Requests
        </h2>
        <div className="rounded-lg border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50 dark:bg-slate-900/50">
                <TableHead>Type</TableHead>
                <TableHead>From</TableHead>
                <TableHead>To</TableHead>
                <TableHead>Days</TableHead>
                <TableHead>Reason</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-20" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {reqLoading ? (
                [...Array(5)].map((_, i) => (
                  <TableRow key={i}>
                    {[...Array(7)].map((_, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                    ))}
                  </TableRow>
                ))
              ) : reqData?.results.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-10 text-slate-400">
                    No leave requests yet.
                  </TableCell>
                </TableRow>
              ) : (
                reqData?.results.map((req) => (
                  <TableRow key={req.id}>
                    <TableCell>
                      <span className="flex items-center gap-1.5 text-sm">
                        <span
                          className="w-2.5 h-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: req.leave_type_color }}
                        />
                        {req.leave_type_name}
                      </span>
                    </TableCell>
                    <TableCell className="text-sm">
                      {format(new Date(req.start_date), 'dd MMM yyyy')}
                    </TableCell>
                    <TableCell className="text-sm">
                      {format(new Date(req.end_date), 'dd MMM yyyy')}
                    </TableCell>
                    <TableCell className="text-sm font-medium">{req.days}</TableCell>
                    <TableCell className="text-sm max-w-[180px] truncate text-slate-500">
                      {req.reason}
                    </TableCell>
                    <TableCell><StatusBadge status={req.status} /></TableCell>
                    <TableCell>
                      {req.status === 'pending' && (
                        <Button
                          variant="ghost" size="sm" className="text-red-600 hover:text-red-700 h-7 px-2"
                          onClick={() => cancelMutation.mutate(req.id)}
                          disabled={cancelMutation.isPending}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      <ApplyLeaveDialog
        open={applyOpen}
        onOpenChange={setApplyOpen}
        leaveTypes={leaveTypes}
        balances={balance?.balances ?? []}
        publicHolidays={holidayDates}
        isPending={applyMutation.isPending}
        onConfirm={async (data) => {
          await applyMutation.mutateAsync(data);
        }}
      />
    </div>
  );
}

// ─── Team Leaves tab ──────────────────────────────────────────────────────────

function TeamLeavesTab() {
  const [approvalTarget, setApprovalTarget] = useState<LeaveRequestListItem | null>(null);
  const [deptFilter,     setDeptFilter]     = useState('');
  const [statusFilter,   setStatusFilter]   = useState('');
  const [page, setPage] = useState(1);

  const { data: departments = [] } = useDepartments();
  const { data: reqData, isLoading } = useLeaveRequests({
    department_id: deptFilter || undefined,
    status:        (statusFilter as LeaveStatus) || undefined,
    page,
    page_size: 20,
  });
  const { data: empBalance } = useLeaveBalance(approvalTarget?.employee_id);
  const approveMutation = useApproveLeave();

  const targetBalance = empBalance?.balances.find(
    (b) => b.leave_type_id === approvalTarget?.leave_type_id,
  ) ?? null;

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <Select value={deptFilter || 'all'} onValueChange={(v) => setDeptFilter(v === 'all' ? '' : v)}>
          <SelectTrigger className="h-8 text-sm w-44">
            <SelectValue placeholder="All departments" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Departments</SelectItem>
            {departments.map((d) => (
              <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={statusFilter || 'all'} onValueChange={(v) => setStatusFilter(v === 'all' ? '' : v)}>
          <SelectTrigger className="h-8 text-sm w-32">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            {(['all', 'pending', 'approved', 'rejected', 'cancelled'] as const).map((s) => (
              <SelectItem key={s} value={s}>{s === 'all' ? 'All statuses' : s}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        {(deptFilter || statusFilter) && (
          <Button
            variant="ghost" size="sm" className="h-8 text-xs gap-1"
            onClick={() => { setDeptFilter(''); setStatusFilter(''); }}
          >
            <Filter className="h-3 w-3" /> Clear
          </Button>
        )}
      </div>

      {/* Table */}
      <div className="rounded-lg border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-slate-50 dark:bg-slate-900/50">
              <TableHead>Employee</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>From</TableHead>
              <TableHead>To</TableHead>
              <TableHead>Days</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="w-28">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              [...Array(5)].map((_, i) => (
                <TableRow key={i}>
                  {[...Array(7)].map((_, j) => (
                    <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : reqData?.results.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-10 text-slate-400">
                  No leave requests found.
                </TableCell>
              </TableRow>
            ) : (
              reqData?.results.map((req) => (
                <TableRow key={req.id}>
                  <TableCell>
                    <p className="text-sm font-medium">{req.employee_name}</p>
                    <p className="text-xs text-slate-400">{req.department_name}</p>
                  </TableCell>
                  <TableCell>
                    <span className="flex items-center gap-1.5 text-sm">
                      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: req.leave_type_color }} />
                      {req.leave_type_name}
                    </span>
                  </TableCell>
                  <TableCell className="text-sm">{format(new Date(req.start_date), 'dd MMM')}</TableCell>
                  <TableCell className="text-sm">{format(new Date(req.end_date), 'dd MMM')}</TableCell>
                  <TableCell className="text-sm font-medium">{req.days}</TableCell>
                  <TableCell><StatusBadge status={req.status} /></TableCell>
                  <TableCell>
                    {req.status === 'pending' && (
                      <div className="flex gap-1">
                        <Button
                          variant="ghost" size="icon" className="h-7 w-7 text-green-600 hover:text-green-700"
                          title="Approve"
                          onClick={() => setApprovalTarget(req)}
                        >
                          <CheckCircle2 className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost" size="icon" className="h-7 w-7 text-red-600 hover:text-red-700"
                          title="Reject"
                          onClick={() => setApprovalTarget(req)}
                        >
                          <XCircle className="h-4 w-4" />
                        </Button>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <LeaveApprovalDialog
        open={!!approvalTarget}
        onOpenChange={(v) => { if (!v) setApprovalTarget(null); }}
        request={approvalTarget}
        postApprovalBalance={targetBalance}
        isPending={approveMutation.isPending}
        onConfirm={async (action, reason) => {
          if (!approvalTarget) return;
          await approveMutation.mutateAsync({
            id:      approvalTarget.id,
            payload: { action, rejection_reason: reason },
          });
          setApprovalTarget(null);
        }}
      />
    </div>
  );
}

// ─── Calendar tab ─────────────────────────────────────────────────────────────

function CalendarTab() {
  const now = new Date();
  const [month, setMonth]           = useState(now.getMonth() + 1);
  const [year,  setYear]            = useState(now.getFullYear());
  const [deptFilter, setDeptFilter] = useState('');

  const { data: entries = [], isLoading } = useLeaveCalendar(month, year, deptFilter || undefined);
  const { data: departments = [] }        = useDepartments();

  return (
    <div className="space-y-4">
      {/* Department filter */}
      <div className="flex items-center gap-3">
        <Building2 className="h-4 w-4 text-slate-400" />
        <Select value={deptFilter || 'all'} onValueChange={(v) => setDeptFilter(v === 'all' ? '' : v)}>
          <SelectTrigger className="h-8 text-sm w-48">
            <SelectValue placeholder="All departments" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Departments</SelectItem>
            {departments.map((d) => (
              <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {isLoading && (
          <span className="text-xs text-slate-400 animate-pulse">Loading…</span>
        )}
      </div>

      <LeaveCalendar
        entries={entries}
        month={month}
        year={year}
        onNavigate={(m, y) => { setMonth(m); setYear(y); }}
      />
    </div>
  );
}

// ─── Settings tab ─────────────────────────────────────────────────────────────

function SettingsTab() {
  const { data: leaveTypes = [], isLoading } = useLeaveTypes();
  const createMutation  = useCreateLeaveType();
  const deleteMutation  = useDeleteLeaveType();
  const { data: holidays = [] } = usePublicHolidays(new Date().getFullYear());
  const createHoliday   = useCreatePublicHoliday();
  const deleteHoliday   = useDeletePublicHoliday();

  const [newType, setNewType] = useState<Partial<LeaveTypeCreate>>({
    name: '', days_allowed: 15, is_paid: true,
    carry_forward: false, max_carry_forward_days: 0,
    requires_document: false, color: '#6366f1', is_active: true,
  });
  const [newHoliday, setNewHoliday] = useState({ date: '', name: '', is_recurring: false });

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Leave types */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Leave Types</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Existing types */}
          <div className="space-y-2">
            {leaveTypes.map((lt) => (
              <div
                key={lt.id}
                className="flex items-center justify-between p-3 rounded-lg border bg-slate-50 dark:bg-slate-800/40"
              >
                <div className="flex items-center gap-3">
                  <span className="w-3 h-3 rounded-full" style={{ backgroundColor: lt.color }} />
                  <div>
                    <p className="text-sm font-medium">{lt.name}</p>
                    <p className="text-xs text-slate-400">
                      {lt.days_allowed} days · {lt.is_paid ? 'Paid' : 'Unpaid'}
                      {lt.carry_forward && ` · Carry fwd (max ${lt.max_carry_forward_days}d)`}
                      {lt.requires_document && ' · Doc required'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={lt.is_active ? 'secondary' : 'outline'} className="text-xs">
                    {lt.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                  <Button
                    variant="ghost" size="icon" className="h-7 w-7 text-red-500"
                    onClick={() => deleteMutation.mutate(lt.id)}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>

          {/* Add new type */}
          <div className="grid grid-cols-2 gap-3 pt-3 border-t dark:border-slate-700">
            <div className="space-y-1">
              <Label className="text-xs">Name</Label>
              <Input
                value={newType.name ?? ''}
                onChange={(e) => setNewType((p) => ({ ...p, name: e.target.value }))}
                placeholder="e.g. Sick Leave"
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Days allowed</Label>
              <Input
                type="number" min={1} max={365}
                value={newType.days_allowed ?? 15}
                onChange={(e) => setNewType((p) => ({ ...p, days_allowed: Number(e.target.value) }))}
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Color</Label>
              <div className="flex gap-2">
                <Input
                  type="color"
                  value={newType.color ?? '#6366f1'}
                  onChange={(e) => setNewType((p) => ({ ...p, color: e.target.value }))}
                  className="h-8 w-12 p-0.5 cursor-pointer"
                />
                <Input
                  value={newType.color ?? '#6366f1'}
                  onChange={(e) => setNewType((p) => ({ ...p, color: e.target.value }))}
                  className="h-8 text-sm flex-1 font-mono"
                />
              </div>
            </div>
            <div className="flex items-end gap-4">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={newType.is_paid ?? true}
                  onChange={(e) => setNewType((p) => ({ ...p, is_paid: e.target.checked }))}
                  className="rounded"
                />
                Paid
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={newType.carry_forward ?? false}
                  onChange={(e) => setNewType((p) => ({ ...p, carry_forward: e.target.checked }))}
                  className="rounded"
                />
                Carry forward
              </label>
            </div>
            <div className="col-span-2">
              <Button
                size="sm"
                className="bg-hrms-600 hover:bg-hrms-700 text-white gap-1.5"
                disabled={!newType.name || createMutation.isPending}
                onClick={() => {
                  createMutation.mutate(newType as LeaveTypeCreate, {
                    onSuccess: () => setNewType({
                      name: '', days_allowed: 15, is_paid: true,
                      carry_forward: false, max_carry_forward_days: 0,
                      requires_document: false, color: '#6366f1', is_active: true,
                    }),
                  });
                }}
              >
                <Plus className="h-3.5 w-3.5" />
                Add Leave Type
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Public holidays */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Public Holidays ({new Date().getFullYear()})</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            {holidays.map((h) => (
              <div key={h.id} className="flex items-center justify-between p-3 rounded-lg border bg-slate-50 dark:bg-slate-800/40">
                <div>
                  <p className="text-sm font-medium">{h.name}</p>
                  <p className="text-xs text-slate-400">
                    {format(new Date(h.date), 'dd MMMM yyyy')}
                    {h.is_recurring && ' · Recurring annually'}
                  </p>
                </div>
                <Button
                  variant="ghost" size="icon" className="h-7 w-7 text-red-500"
                  onClick={() => deleteHoliday.mutate({ id: h.id, year: new Date(h.date).getFullYear() })}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </div>

          {/* Add holiday */}
          <div className="grid grid-cols-2 gap-3 pt-3 border-t dark:border-slate-700">
            <div className="space-y-1">
              <Label className="text-xs">Date</Label>
              <Input
                type="date"
                value={newHoliday.date}
                onChange={(e) => setNewHoliday((p) => ({ ...p, date: e.target.value }))}
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Name</Label>
              <Input
                value={newHoliday.name}
                onChange={(e) => setNewHoliday((p) => ({ ...p, name: e.target.value }))}
                placeholder="e.g. Eid ul-Fitr"
                className="h-8 text-sm"
              />
            </div>
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={newHoliday.is_recurring}
                  onChange={(e) => setNewHoliday((p) => ({ ...p, is_recurring: e.target.checked }))}
                  className="rounded"
                />
                Recurring annually
              </label>
            </div>
            <div className="flex items-end">
              <Button
                size="sm"
                className="bg-hrms-600 hover:bg-hrms-700 text-white gap-1.5"
                disabled={!newHoliday.date || !newHoliday.name || createHoliday.isPending}
                onClick={() => {
                  createHoliday.mutate(newHoliday, {
                    onSuccess: () => setNewHoliday({ date: '', name: '', is_recurring: false }),
                  });
                }}
              >
                <Plus className="h-3.5 w-3.5" />
                Add Holiday
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function LeavePage() {
  const canApprove = useAuthStore((s) => s.hasPermission('leave', 'approve'));
  const canManage  = useAuthStore((s) => s.hasPermission('leave', 'manage'));

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-2 px-6 py-4 border-b bg-white dark:bg-slate-950">
        <CalendarDays className="h-5 w-5 text-hrms-600" />
        <h1 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Leave Management</h1>
      </div>

      <div className="flex-1 overflow-auto p-6">
        <Tabs defaultValue="my-leaves">
          <TabsList className="mb-6">
            <TabsTrigger value="my-leaves">My Leaves</TabsTrigger>
            {canApprove && (
              <TabsTrigger value="team-leaves">Team Leaves</TabsTrigger>
            )}
            <TabsTrigger value="calendar">Calendar</TabsTrigger>
            {canManage && (
              <TabsTrigger value="settings">
                <Settings className="h-3.5 w-3.5 mr-1.5" />
                Settings
              </TabsTrigger>
            )}
          </TabsList>

          <TabsContent value="my-leaves">
            <MyLeavesTab />
          </TabsContent>

          {canApprove && (
            <TabsContent value="team-leaves">
              <TeamLeavesTab />
            </TabsContent>
          )}

          <TabsContent value="calendar">
            <CalendarTab />
          </TabsContent>

          {canManage && (
            <TabsContent value="settings">
              <SettingsTab />
            </TabsContent>
          )}
        </Tabs>
      </div>
    </div>
  );
}
