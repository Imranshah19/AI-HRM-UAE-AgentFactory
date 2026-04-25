'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Users, UserCheck, CalendarClock, Briefcase,
  Plus, PlayCircle, UserPlus,
  TrendingUp, TrendingDown, Minus,
} from 'lucide-react';
import {
  ResponsiveContainer, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend,
} from 'recharts';

import { useAuthStore }  from '@/stores/authStore';
import { cn }            from '@/lib/utils';
import { formatDate }    from '@/lib/utils';
import { Button }        from '@/components/ui/button';
import { Skeleton }      from '@/components/ui/skeleton';
import {
  Card, CardContent, CardHeader, CardTitle,
} from '@/components/ui/card';
import { Badge }  from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { useDashboardStats, useHeadcountReport, useAttendanceReport } from '@/hooks/useReports';
import { AIInsightsDashboard } from '@/components/ai/AIInsightsDashboard';
import { ChatWidget }          from '@/components/ai/ChatWidget';

// ─── Types ────────────────────────────────────────────────────────────────────

interface StatCard {
  title:  string;
  value:  number | string;
  icon:   React.ElementType;
  color:  string;
  bg:     string;
  trend?: { value: number; label: string };
}

interface AuditEntry {
  id:             string;
  action:         string;
  resource:       string;
  resource_label: string | null;
  user_email:     string | null;
  created_at:     string;
}

// ─── Stat Card ────────────────────────────────────────────────────────────────

function StatCardSkeleton() {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-8 w-16" />
            <Skeleton className="h-3 w-20" />
          </div>
          <Skeleton className="h-12 w-12 rounded-xl" />
        </div>
      </CardContent>
    </Card>
  );
}

function StatCardUI({ card }: { card: StatCard }) {
  const Icon = card.icon;
  return (
    <Card className="hover:shadow-card-hover transition-shadow">
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">{card.title}</p>
            <p className="text-3xl font-bold text-slate-800 dark:text-slate-100 mt-1">
              {card.value}
            </p>
            {card.trend && (
              <div className="flex items-center gap-1 mt-1">
                {card.trend.value > 0 ? (
                  <TrendingUp className="h-3 w-3 text-green-500" />
                ) : card.trend.value < 0 ? (
                  <TrendingDown className="h-3 w-3 text-red-500" />
                ) : (
                  <Minus className="h-3 w-3 text-slate-400" />
                )}
                <span className={cn(
                  'text-xs font-medium',
                  card.trend.value > 0 ? 'text-green-600' :
                  card.trend.value < 0 ? 'text-red-600' : 'text-slate-400',
                )}>
                  {card.trend.label}
                </span>
              </div>
            )}
          </div>
          <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center', card.bg)}>
            <Icon className={cn('h-5 w-5', card.color)} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Greeting ────────────────────────────────────────────────────────────────

function getGreeting(h: number): string {
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const router = useRouter();
  const user   = useAuthStore((s) => s.user);

  // Derive date values client-side only to avoid SSR/client hydration mismatch
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => { setNow(new Date()); }, []);

  const CURRENT_MONTH = now ? now.getMonth() + 1 : new Date().getMonth() + 1;
  const CURRENT_YEAR  = now ? now.getFullYear()  : new Date().getFullYear();

  const { data: dashStats, isLoading: sLoading }  = useDashboardStats();
  const { data: headcount, isLoading: hLoading }  = useHeadcountReport();
  const { data: attnData,  isLoading: aLoading }  = useAttendanceReport(CURRENT_MONTH, CURRENT_YEAR);

  const loading = sLoading;
  const auditFeed: AuditEntry[] = [];

  // Chart data derived from real API
  const deptData = headcount?.by_department.map((d) => ({ name: d.department, count: d.count })) ?? [];
  const attendance = attnData?.daily_trend.slice(-7).map((d) => ({
    day: d.date.slice(8), present: d.present, absent: d.absent,
  })) ?? [];

  const statCards: StatCard[] = [
    {
      title: 'Total Employees',
      value: loading ? '—' : (dashStats?.total_employees ?? 0),
      icon:  Users,
      color: 'text-hrms-600',
      bg:    'bg-hrms-50 dark:bg-hrms-950/30',
    },
    {
      title: 'Present Today',
      value: loading ? '—' : (dashStats?.present_today ?? 0),
      icon:  UserCheck,
      color: 'text-green-600',
      bg:    'bg-green-50 dark:bg-green-950/30',
    },
    {
      title: 'Pending Leaves',
      value: loading ? '—' : (dashStats?.pending_leaves ?? 0),
      icon:  CalendarClock,
      color: 'text-amber-600',
      bg:    'bg-amber-50 dark:bg-amber-950/30',
    },
    {
      title: 'Open Positions',
      value: loading ? '—' : (dashStats?.open_positions ?? 0),
      icon:  Briefcase,
      color: 'text-purple-600',
      bg:    'bg-purple-50 dark:bg-purple-950/30',
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">
            {now ? getGreeting(now.getHours()) : ''}, {user?.first_name ?? 'there'} 👋
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5" suppressHydrationWarning>
            {now?.toLocaleDateString('en-PK', {
              weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
            }) ?? ''}
          </p>
        </div>

        {/* Quick actions */}
        <div className="hidden sm:flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => router.push('/employees/new')}
            className="gap-1.5"
          >
            <UserPlus className="h-3.5 w-3.5" />
            Add Employee
          </Button>
          <Button
            size="sm"
            className="bg-hrms-600 hover:bg-hrms-700 text-white gap-1.5"
            onClick={() => router.push('/payroll')}
          >
            <PlayCircle className="h-3.5 w-3.5" />
            Run Payroll
          </Button>
        </div>
      </div>

      {/* ── Stat cards ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />)
          : statCards.map((card) => <StatCardUI key={card.title} card={card} />)
        }
      </div>

      {/* ── Charts row ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Headcount by department */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-slate-700 dark:text-slate-300">
              Headcount by Department
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-52 w-full" />
            ) : (
              <ResponsiveContainer width="100%" height={210}>
                <BarChart data={deptData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 11, fill: '#94a3b8' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: '#94a3b8' }}
                    axisLine={false}
                    tickLine={false}
                    allowDecimals={false}
                  />
                  <RechartsTooltip
                    contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }}
                  />
                  <Bar dataKey="count" fill="#2563eb" radius={[4, 4, 0, 0]} name="Employees" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Attendance this week */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-slate-700 dark:text-slate-300">
              Attendance This Week
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-52 w-full" />
            ) : (
              <ResponsiveContainer width="100%" height={210}>
                <LineChart data={attendance} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis
                    dataKey="day"
                    tick={{ fontSize: 11, fill: '#94a3b8' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: '#94a3b8' }}
                    axisLine={false}
                    tickLine={false}
                    allowDecimals={false}
                  />
                  <RechartsTooltip
                    contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line
                    type="monotone"
                    dataKey="present"
                    stroke="#22c55e"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    name="Present"
                  />
                  <Line
                    type="monotone"
                    dataKey="absent"
                    stroke="#ef4444"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    name="Absent"
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── AI Insights ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-1">
          <AIInsightsDashboard />
        </div>

        {/* Placeholder to maintain grid balance */}
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                Recent Activity
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-10 text-slate-400 text-sm">
                No recent activity yet.
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* ── Bottom row ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Quick actions */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold text-slate-700 dark:text-slate-300">
              Quick Actions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {[
              { label: 'Add Employee',  icon: UserPlus,    href: '/employees/new',   color: 'text-hrms-600' },
              { label: 'Post Job',      icon: Briefcase,   href: '/recruitment/new', color: 'text-purple-600' },
              { label: 'Run Payroll',   icon: PlayCircle,  href: '/payroll',         color: 'text-green-600' },
              { label: 'Add Department', icon: Plus,       href: '/departments',     color: 'text-amber-600' },
            ].map(({ label, icon: Icon, href, color }) => (
              <Button
                key={label}
                variant="outline"
                className="w-full justify-start gap-2 h-9 text-sm"
                onClick={() => router.push(href)}
              >
                <Icon className={cn('h-4 w-4', color)} />
                {label}
              </Button>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* ── Chat Widget ─────────────────────────────────────────────────── */}
      <ChatWidget />
    </div>
  );
}
