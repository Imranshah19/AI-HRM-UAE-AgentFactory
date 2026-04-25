'use client';

import { useState } from 'react';
import {
  BarChart2, Users, UserMinus, CalendarCheck, DollarSign,
  CalendarClock, Briefcase, Download, TrendingUp, TrendingDown,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart, Bar,
  LineChart, Line,
  PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, Legend,
} from 'recharts';

import { Button }   from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { cn }   from '@/lib/utils';

import {
  useDashboardStats, useHeadcountReport, useTurnoverReport,
  useAttendanceReport, usePayrollReport, useLeaveReport, useRecruitmentReport,
} from '@/hooks/useReports';
import { exportUrl } from '@/lib/api/reports';

// ─── Constants ────────────────────────────────────────────────────────────────

const CURRENT_YEAR  = new Date().getFullYear();
const CURRENT_MONTH = new Date().getMonth() + 1;
const YEARS  = Array.from({ length: 5 }, (_, i) => CURRENT_YEAR - i);
const MONTHS = [
  { label: 'January', value: 1 }, { label: 'February', value: 2 },
  { label: 'March',   value: 3 }, { label: 'April',    value: 4 },
  { label: 'May',     value: 5 }, { label: 'June',     value: 6 },
  { label: 'July',    value: 7 }, { label: 'August',   value: 8 },
  { label: 'September', value: 9 }, { label: 'October', value: 10 },
  { label: 'November',  value: 11 }, { label: 'December', value: 12 },
];

const PIE_COLORS = ['#2563eb', '#7c3aed', '#059669', '#d97706', '#dc2626', '#0891b2'];

// ─── Nav items ────────────────────────────────────────────────────────────────

type ReportType =
  | 'dashboard' | 'headcount' | 'turnover'
  | 'attendance' | 'payroll' | 'leave' | 'recruitment';

const NAV_ITEMS: { id: ReportType; label: string; icon: React.ElementType }[] = [
  { id: 'dashboard',   label: 'Dashboard Overview', icon: BarChart2     },
  { id: 'headcount',   label: 'Headcount Report',   icon: Users         },
  { id: 'attendance',  label: 'Attendance Report',  icon: CalendarCheck },
  { id: 'payroll',     label: 'Payroll Report',     icon: DollarSign    },
  { id: 'leave',       label: 'Leave Report',       icon: CalendarClock },
  { id: 'turnover',    label: 'Turnover Report',    icon: UserMinus     },
  { id: 'recruitment', label: 'Recruitment Report', icon: Briefcase     },
];

// ─── Dashboard Overview ───────────────────────────────────────────────────────

function DashboardOverview() {
  const { data: stats,     isLoading: sLoading }  = useDashboardStats();
  const { data: headcount, isLoading: hLoading }  = useHeadcountReport();
  const { data: attendance, isLoading: aLoading } = useAttendanceReport(CURRENT_MONTH, CURRENT_YEAR);
  const { data: payroll,    isLoading: pLoading } = usePayrollReport(CURRENT_YEAR);
  const { data: turnover,   isLoading: tLoading } = useTurnoverReport(CURRENT_YEAR);

  const statCards = [
    {
      label: 'Total Employees', value: stats?.total_employees ?? 0,
      icon: Users, color: 'text-blue-600', bg: 'bg-blue-50',
    },
    {
      label: 'Present Today', value: stats?.present_today ?? 0,
      icon: CalendarCheck, color: 'text-green-600', bg: 'bg-green-50',
    },
    {
      label: 'Pending Leaves', value: stats?.pending_leaves ?? 0,
      icon: CalendarClock, color: 'text-amber-600', bg: 'bg-amber-50',
    },
    {
      label: 'Open Positions', value: stats?.open_positions ?? 0,
      icon: Briefcase, color: 'text-purple-600', bg: 'bg-purple-50',
    },
    {
      label: 'Payroll Status',
      value: stats?.payroll_due ? 'Due' : 'Processed',
      icon: DollarSign,
      color: stats?.payroll_due ? 'text-red-600' : 'text-green-600',
      bg: stats?.payroll_due ? 'bg-red-50' : 'bg-green-50',
    },
    {
      label: 'Upcoming Birthdays', value: stats?.upcoming_birthdays.length ?? 0,
      icon: TrendingUp, color: 'text-pink-600', bg: 'bg-pink-50',
    },
  ];

  const deptData  = headcount?.by_department.map((d) => ({ name: d.department, count: d.count })) ?? [];
  const attnTrend = attendance?.daily_trend.slice(-14).map((d) => ({
    date: d.date.slice(5), present: d.present, absent: d.absent,
  })) ?? [];
  const payrollTrend = payroll?.months.map((m) => ({
    month: m.month, gross: m.gross / 1000, net: m.net / 1000,
  })) ?? [];
  const turnoverData = turnover?.months.map((m) => ({
    month: m.month, rate: m.turnover_rate,
  })) ?? [];

  return (
    <div className="space-y-6">
      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {statCards.map((c) => {
          const Icon = c.icon;
          return (
            <Card key={c.label}>
              <CardContent className="p-4">
                {sLoading ? <Skeleton className="h-16 w-full" /> : (
                  <div className="flex flex-col gap-2">
                    <div className={cn('w-9 h-9 rounded-lg flex items-center justify-center', c.bg)}>
                      <Icon className={cn('h-4 w-4', c.color)} />
                    </div>
                    <p className="text-2xl font-bold text-slate-800">{c.value}</p>
                    <p className="text-xs text-slate-500">{c.label}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Upcoming birthdays */}
      {(stats?.upcoming_birthdays.length ?? 0) > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Upcoming Birthdays (next 30 days)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {stats!.upcoming_birthdays.map((b) => (
                <Badge key={b.employee_id} variant="secondary" className="text-xs">
                  {b.full_name} — {b.birthday} ({b.days_until === 0 ? 'Today!' : `in ${b.days_until}d`})
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Headcount by Department</CardTitle>
          </CardHeader>
          <CardContent>
            {hLoading ? <Skeleton className="h-52 w-full" /> : (
              <ResponsiveContainer width="100%" height={210}>
                <BarChart data={deptData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <RechartsTooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                  <Bar dataKey="count" fill="#2563eb" radius={[4, 4, 0, 0]} name="Employees" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Attendance Trend (last 14 days)</CardTitle>
          </CardHeader>
          <CardContent>
            {aLoading ? <Skeleton className="h-52 w-full" /> : (
              <ResponsiveContainer width="100%" height={210}>
                <LineChart data={attnTrend} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <RechartsTooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line type="monotone" dataKey="present" stroke="#22c55e" strokeWidth={2} dot={false} name="Present" />
                  <Line type="monotone" dataKey="absent"  stroke="#ef4444" strokeWidth={2} dot={false} name="Absent" />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Payroll Trend {CURRENT_YEAR} (PKR 000s)</CardTitle>
          </CardHeader>
          <CardContent>
            {pLoading ? <Skeleton className="h-52 w-full" /> : (
              <ResponsiveContainer width="100%" height={210}>
                <BarChart data={payrollTrend} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <RechartsTooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} formatter={(v: number) => `${v.toFixed(0)}K`} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="gross" fill="#7c3aed" radius={[3, 3, 0, 0]} name="Gross" />
                  <Bar dataKey="net"   fill="#059669" radius={[3, 3, 0, 0]} name="Net" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Turnover Rate {CURRENT_YEAR} (%)</CardTitle>
          </CardHeader>
          <CardContent>
            {tLoading ? <Skeleton className="h-52 w-full" /> : (
              <ResponsiveContainer width="100%" height={210}>
                <LineChart data={turnoverData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <RechartsTooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} formatter={(v: number) => `${v.toFixed(1)}%`} />
                  <Line type="monotone" dataKey="rate" stroke="#dc2626" strokeWidth={2} dot={{ r: 3 }} name="Turnover %" />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ─── Headcount Report ─────────────────────────────────────────────────────────

function HeadcountSection() {
  const { data, isLoading } = useHeadcountReport();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">Total: <strong>{data?.total ?? '—'}</strong> employees</p>
        <Button size="sm" variant="outline" asChild>
          <a href={exportUrl('headcount')} download>
            <Download className="h-3.5 w-3.5 mr-1.5" /> Export Excel
          </a>
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">By Department</CardTitle></CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-52 w-full" /> : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={data?.by_department.map((d) => ({ name: d.department, count: d.count }))} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <RechartsTooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                  <Bar dataKey="count" fill="#2563eb" radius={[4, 4, 0, 0]} name="Employees" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">By Gender</CardTitle></CardHeader>
          <CardContent className="flex items-center justify-center">
            {isLoading ? <Skeleton className="h-52 w-full" /> : (
              <PieChart width={220} height={220}>
                <Pie
                  data={data?.by_gender.map((g) => ({ name: g.gender || 'Unknown', value: g.count }))}
                  cx={110} cy={100} outerRadius={80}
                  dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                >
                  {data?.by_gender.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <RechartsTooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
              </PieChart>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">Department Breakdown</CardTitle></CardHeader>
        <CardContent className="p-0">
          {isLoading ? <Skeleton className="h-40 w-full m-4" /> : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Department</TableHead>
                  <TableHead className="text-right">Count</TableHead>
                  <TableHead className="text-right">% of Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.by_department.map((d) => (
                  <TableRow key={d.department}>
                    <TableCell className="font-medium">{d.department}</TableCell>
                    <TableCell className="text-right">{d.count}</TableCell>
                    <TableCell className="text-right">{d.percentage.toFixed(1)}%</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Attendance Report ────────────────────────────────────────────────────────

function AttendanceSection() {
  const [month, setMonth] = useState(CURRENT_MONTH);
  const [year,  setYear]  = useState(CURRENT_YEAR);
  const { data, isLoading } = useAttendanceReport(month, year);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 justify-between">
        <div className="flex gap-2">
          <Select value={String(month)} onValueChange={(v) => setMonth(Number(v))}>
            <SelectTrigger className="h-8 w-36 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {MONTHS.map((m) => (
                <SelectItem key={m.value} value={String(m.value)}>{m.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={String(year)} onValueChange={(v) => setYear(Number(v))}>
            <SelectTrigger className="h-8 w-24 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {YEARS.map((y) => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <Button size="sm" variant="outline" asChild>
          <a href={exportUrl('attendance', { month, year })} download>
            <Download className="h-3.5 w-3.5 mr-1.5" /> Export Excel
          </a>
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Daily Trend</CardTitle></CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-52 w-full" /> : (
              <ResponsiveContainer width="100%" height={210}>
                <LineChart
                  data={data?.daily_trend.map((d) => ({ date: d.date.slice(8), present: d.present, absent: d.absent, late: d.late }))}
                  margin={{ top: 4, right: 4, left: -20, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <RechartsTooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line type="monotone" dataKey="present" stroke="#22c55e" strokeWidth={2} dot={false} name="Present" />
                  <Line type="monotone" dataKey="absent"  stroke="#ef4444" strokeWidth={2} dot={false} name="Absent" />
                  <Line type="monotone" dataKey="late"    stroke="#f59e0b" strokeWidth={2} dot={false} name="Late" />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">By Department</CardTitle></CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-52 w-full" /> : (
              <ResponsiveContainer width="100%" height={210}>
                <BarChart
                  data={data?.by_dept.map((d) => ({ name: d.department, present: d.present_pct, absent: d.absent_pct }))}
                  margin={{ top: 4, right: 4, left: -20, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} domain={[0, 100]} />
                  <RechartsTooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} formatter={(v: number) => `${v.toFixed(1)}%`} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="present" fill="#22c55e" stackId="a" name="Present %" />
                  <Bar dataKey="absent"  fill="#ef4444" stackId="a" name="Absent %" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">Department Summary</CardTitle></CardHeader>
        <CardContent className="p-0">
          {isLoading ? <Skeleton className="h-40 w-full m-4" /> : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Department</TableHead>
                  <TableHead className="text-right">Expected</TableHead>
                  <TableHead className="text-right">Present</TableHead>
                  <TableHead className="text-right">Absent</TableHead>
                  <TableHead className="text-right">Late</TableHead>
                  <TableHead className="text-right">Present %</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.by_dept.map((d) => (
                  <TableRow key={d.department}>
                    <TableCell className="font-medium">{d.department}</TableCell>
                    <TableCell className="text-right">{d.total_expected}</TableCell>
                    <TableCell className="text-right text-green-600">{d.present}</TableCell>
                    <TableCell className="text-right text-red-600">{d.absent}</TableCell>
                    <TableCell className="text-right text-amber-600">{d.late}</TableCell>
                    <TableCell className="text-right">{d.present_pct.toFixed(1)}%</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Payroll Report ───────────────────────────────────────────────────────────

function PayrollSection() {
  const [year, setYear] = useState(CURRENT_YEAR);
  const { data, isLoading } = usePayrollReport(year);

  const chartData = data?.months.map((m) => ({
    month: m.month, gross: m.gross / 1000, net: m.net / 1000, tax: m.tax / 1000,
  })) ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Select value={String(year)} onValueChange={(v) => setYear(Number(v))}>
          <SelectTrigger className="h-8 w-24 text-xs"><SelectValue /></SelectTrigger>
          <SelectContent>
            {YEARS.map((y) => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}
          </SelectContent>
        </Select>
        <Button size="sm" variant="outline" asChild>
          <a href={exportUrl('payroll', { year })} download>
            <Download className="h-3.5 w-3.5 mr-1.5" /> Export Excel
          </a>
        </Button>
      </div>

      {data && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { label: 'Total Gross', value: data.totals.gross },
            { label: 'Total Net',   value: data.totals.net },
            { label: 'Total Tax',   value: data.totals.tax },
            { label: 'Total EOBI',  value: data.totals.eobi },
          ].map((c) => (
            <Card key={c.label}>
              <CardContent className="p-4">
                <p className="text-xs text-slate-500">{c.label}</p>
                <p className="text-xl font-bold text-slate-800 mt-1">
                  {c.value.toLocaleString('en-PK', { style: 'currency', currency: 'PKR', maximumFractionDigits: 0 })}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">Monthly Payroll (PKR 000s)</CardTitle></CardHeader>
        <CardContent>
          {isLoading ? <Skeleton className="h-52 w-full" /> : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <RechartsTooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} formatter={(v: number) => `${v.toFixed(0)}K`} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="gross" fill="#7c3aed" radius={[3, 3, 0, 0]} name="Gross" />
                <Bar dataKey="net"   fill="#059669" radius={[3, 3, 0, 0]} name="Net" />
                <Bar dataKey="tax"   fill="#dc2626" radius={[3, 3, 0, 0]} name="Tax" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">Monthly Breakdown</CardTitle></CardHeader>
        <CardContent className="p-0">
          {isLoading ? <Skeleton className="h-40 w-full m-4" /> : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Month</TableHead>
                  <TableHead className="text-right">Headcount</TableHead>
                  <TableHead className="text-right">Gross</TableHead>
                  <TableHead className="text-right">Net</TableHead>
                  <TableHead className="text-right">Tax</TableHead>
                  <TableHead className="text-right">EOBI</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.months.map((m) => (
                  <TableRow key={m.month_num}>
                    <TableCell className="font-medium">{m.month}</TableCell>
                    <TableCell className="text-right">{m.headcount}</TableCell>
                    <TableCell className="text-right">{m.gross.toLocaleString()}</TableCell>
                    <TableCell className="text-right">{m.net.toLocaleString()}</TableCell>
                    <TableCell className="text-right">{m.tax.toLocaleString()}</TableCell>
                    <TableCell className="text-right">{m.eobi.toLocaleString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Leave Report ─────────────────────────────────────────────────────────────

function LeaveSection() {
  const [year, setYear] = useState(CURRENT_YEAR);
  const { data, isLoading } = useLeaveReport(year);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Select value={String(year)} onValueChange={(v) => setYear(Number(v))}>
          <SelectTrigger className="h-8 w-24 text-xs"><SelectValue /></SelectTrigger>
          <SelectContent>
            {YEARS.map((y) => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}
          </SelectContent>
        </Select>
        <Button size="sm" variant="outline" asChild>
          <a href={exportUrl('leave', { year })} download>
            <Download className="h-3.5 w-3.5 mr-1.5" /> Export Excel
          </a>
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">By Leave Type</CardTitle></CardHeader>
          <CardContent className="flex items-center justify-center">
            {isLoading ? <Skeleton className="h-52 w-full" /> : (
              <PieChart width={220} height={220}>
                <Pie
                  data={data?.by_type.map((t) => ({ name: t.leave_type, value: t.total_days }))}
                  cx={110} cy={100} outerRadius={80}
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value}d`}
                  labelLine={false}
                >
                  {data?.by_type.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Pie>
                <RechartsTooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
              </PieChart>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Monthly Trend (days taken)</CardTitle></CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-52 w-full" /> : (
              <ResponsiveContainer width="100%" height={210}>
                <BarChart
                  data={data?.monthly_trend.map((m) => ({ month: m.month, days: m.days_taken }))}
                  margin={{ top: 4, right: 4, left: -20, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <RechartsTooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                  <Bar dataKey="days" fill="#0891b2" radius={[4, 4, 0, 0]} name="Days Taken" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">By Department</CardTitle></CardHeader>
        <CardContent className="p-0">
          {isLoading ? <Skeleton className="h-40 w-full m-4" /> : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Department</TableHead>
                  <TableHead className="text-right">Total Days</TableHead>
                  <TableHead className="text-right">Avg per Employee</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.by_department.map((d) => (
                  <TableRow key={d.department}>
                    <TableCell className="font-medium">{d.department}</TableCell>
                    <TableCell className="text-right">{d.total_days}</TableCell>
                    <TableCell className="text-right">{d.avg_per_emp.toFixed(1)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Turnover Report ──────────────────────────────────────────────────────────

function TurnoverSection() {
  const [year, setYear] = useState(CURRENT_YEAR);
  const { data, isLoading } = useTurnoverReport(year);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Select value={String(year)} onValueChange={(v) => setYear(Number(v))}>
          <SelectTrigger className="h-8 w-24 text-xs"><SelectValue /></SelectTrigger>
          <SelectContent>
            {YEARS.map((y) => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}
          </SelectContent>
        </Select>
        <div className="flex items-center gap-3">
          {data && (
            <span className="text-sm text-slate-500">
              Total exits: <strong>{data.total_exits}</strong> &nbsp;|&nbsp;
              Avg rate: <strong>{data.avg_rate.toFixed(1)}%</strong>
            </span>
          )}
          <Button size="sm" variant="outline" asChild>
            <a href={exportUrl('turnover', { year })} download>
              <Download className="h-3.5 w-3.5 mr-1.5" /> Export Excel
            </a>
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Monthly Exits</CardTitle></CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-52 w-full" /> : (
              <ResponsiveContainer width="100%" height={210}>
                <BarChart
                  data={data?.months.map((m) => ({ month: m.month, resignations: m.resignations, terminations: m.terminations }))}
                  margin={{ top: 4, right: 4, left: -20, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <RechartsTooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="resignations"  fill="#f59e0b" radius={[3, 3, 0, 0]} name="Resignations"  stackId="a" />
                  <Bar dataKey="terminations"  fill="#dc2626" radius={[3, 3, 0, 0]} name="Terminations"  stackId="a" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Monthly Turnover Rate (%)</CardTitle></CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-52 w-full" /> : (
              <ResponsiveContainer width="100%" height={210}>
                <LineChart
                  data={data?.months.map((m) => ({ month: m.month, rate: m.turnover_rate }))}
                  margin={{ top: 4, right: 4, left: -20, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <RechartsTooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} formatter={(v: number) => `${v.toFixed(1)}%`} />
                  <Line type="monotone" dataKey="rate" stroke="#dc2626" strokeWidth={2} dot={{ r: 3 }} name="Turnover %" />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">Monthly Detail</CardTitle></CardHeader>
        <CardContent className="p-0">
          {isLoading ? <Skeleton className="h-40 w-full m-4" /> : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Month</TableHead>
                  <TableHead className="text-right">Resignations</TableHead>
                  <TableHead className="text-right">Terminations</TableHead>
                  <TableHead className="text-right">Total Exits</TableHead>
                  <TableHead className="text-right">Headcount</TableHead>
                  <TableHead className="text-right">Rate %</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.months.map((m) => (
                  <TableRow key={m.month_num}>
                    <TableCell className="font-medium">{m.month}</TableCell>
                    <TableCell className="text-right">{m.resignations}</TableCell>
                    <TableCell className="text-right">{m.terminations}</TableCell>
                    <TableCell className="text-right">{m.total_exits}</TableCell>
                    <TableCell className="text-right">{m.headcount}</TableCell>
                    <TableCell className="text-right">
                      <span className={m.turnover_rate > 5 ? 'text-red-600 font-medium' : ''}>
                        {m.turnover_rate.toFixed(1)}%
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Recruitment Report ───────────────────────────────────────────────────────

function RecruitmentSection() {
  const [year, setYear] = useState(CURRENT_YEAR);
  const { data, isLoading } = useRecruitmentReport(year);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Select value={String(year)} onValueChange={(v) => setYear(Number(v))}>
          <SelectTrigger className="h-8 w-24 text-xs"><SelectValue /></SelectTrigger>
          <SelectContent>
            {YEARS.map((y) => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}
          </SelectContent>
        </Select>
        <Button size="sm" variant="outline" asChild>
          <a href={exportUrl('recruitment', { year })} download>
            <Download className="h-3.5 w-3.5 mr-1.5" /> Export Excel
          </a>
        </Button>
      </div>

      {data && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { label: 'Job Postings',      value: data.total_postings },
            { label: 'Applications',      value: data.total_applications },
            { label: 'Hires',             value: data.total_hires },
            { label: 'Avg Days to Hire',  value: Math.round(data.avg_time_to_hire) },
          ].map((c) => (
            <Card key={c.label}>
              <CardContent className="p-4">
                <p className="text-xs text-slate-500">{c.label}</p>
                <p className="text-2xl font-bold text-slate-800 mt-1">{c.value}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Monthly Applications & Hires</CardTitle></CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-52 w-full" /> : (
              <ResponsiveContainer width="100%" height={210}>
                <BarChart
                  data={data?.monthly.map((m) => ({ month: m.month, applications: m.applications, hires: m.hires }))}
                  margin={{ top: 4, right: 4, left: -20, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <RechartsTooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="applications" fill="#7c3aed" radius={[3, 3, 0, 0]} name="Applications" />
                  <Bar dataKey="hires"         fill="#059669" radius={[3, 3, 0, 0]} name="Hires" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">By Department</CardTitle></CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-52 w-full" /> : (
              <ResponsiveContainer width="100%" height={210}>
                <BarChart
                  data={data?.by_department.map((d) => ({ name: d.department, applications: d.applications, hires: d.hires }))}
                  layout="vertical"
                  margin={{ top: 4, right: 4, left: 60, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis type="number" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={55} />
                  <RechartsTooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="applications" fill="#7c3aed" radius={[0, 3, 3, 0]} name="Applications" />
                  <Bar dataKey="hires"         fill="#059669" radius={[0, 3, 3, 0]} name="Hires" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

const SECTION_MAP: Record<ReportType, React.ComponentType> = {
  dashboard:   DashboardOverview,
  headcount:   HeadcountSection,
  attendance:  AttendanceSection,
  payroll:     PayrollSection,
  leave:       LeaveSection,
  turnover:    TurnoverSection,
  recruitment: RecruitmentSection,
};

export default function ReportsPage() {
  const [active, setActive] = useState<ReportType>('dashboard');
  const ActiveSection = SECTION_MAP[active];

  return (
    <div className="flex gap-6 max-w-screen-2xl mx-auto">
      {/* Sidebar */}
      <aside className="w-52 shrink-0 hidden lg:block">
        <nav className="space-y-0.5">
          {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActive(id)}
              className={cn(
                'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors text-left',
                active === id
                  ? 'bg-hrms-50 text-hrms-700 font-medium dark:bg-hrms-950/30 dark:text-hrms-300'
                  : 'text-slate-600 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-800',
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </button>
          ))}
        </nav>
      </aside>

      {/* Mobile tab strip */}
      <div className="lg:hidden flex gap-1 overflow-x-auto pb-1 w-full mb-2">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActive(id)}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs whitespace-nowrap transition-colors',
              active === id
                ? 'bg-hrms-600 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200',
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">
            {NAV_ITEMS.find((n) => n.id === active)?.label}
          </h1>
        </div>
        <ActiveSection />
      </div>
    </div>
  );
}
