'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Brain, RefreshCw, Download, AlertCircle, AlertTriangle,
  Info, CheckCircle2, ShieldAlert, TrendingDown, Users,
  MessageSquare, Zap, Filter,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts';

import { Button }   from '@/components/ui/button';
import { Badge }    from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';

import {
  useAttritionOverview,
  useAIInsights,
  useAnomalies,
  useBulkAttrition,
} from '@/hooks/useAI';
import type { Anomaly, AnomalySeverity } from '@/types/ai';

// ─── Tier helpers ────────────────────────────────────────────────────────────

const TIER_COLORS: Record<string, string> = {
  Low:      '#22c55e',
  Medium:   '#f59e0b',
  High:     '#f97316',
  Critical: '#ef4444',
};

const TIER_BADGE: Record<string, string> = {
  Low:      'bg-green-100 text-green-700',
  Medium:   'bg-amber-100 text-amber-700',
  High:     'bg-orange-100 text-orange-700',
  Critical: 'bg-red-100 text-red-700',
};

const SEV_CONFIG: Record<AnomalySeverity, {
  icon: React.ElementType; color: string; bg: string; label: string;
}> = {
  high:   { icon: AlertCircle,   color: 'text-red-500',   bg: 'bg-red-50',   label: 'High'   },
  medium: { icon: AlertTriangle, color: 'text-amber-500', bg: 'bg-amber-50', label: 'Medium' },
  low:    { icon: Info,          color: 'text-blue-500',  bg: 'bg-blue-50',  label: 'Low'    },
};

// ─── Tab 1: Attrition Risk ────────────────────────────────────────────────────

function AttritionTab() {
  const router = useRouter();
  const [deptFilter, setDeptFilter] = useState('all');
  const [tierFilter, setTierFilter] = useState('all');

  const { data: overview, isLoading, refetch } = useAttritionOverview();
  const bulkMutation = useBulkAttrition();

  const employees = overview?.high_risk_employees ?? [];

  // Build dept chart data from employees list
  const deptMap: Record<string, Record<string, number>> = {};
  employees.forEach((e) => {
    const dept = e.department ?? 'Unknown';
    if (!deptMap[dept]) deptMap[dept] = { Low: 0, Medium: 0, High: 0, Critical: 0 };
    deptMap[dept][e.tier] = (deptMap[dept][e.tier] ?? 0) + 1;
  });
  const deptChartData = Object.entries(deptMap).map(([dept, counts]) => ({
    dept: dept.length > 10 ? dept.slice(0, 10) + '…' : dept,
    ...counts,
  }));

  // Filter
  const filtered = employees.filter((e) => {
    const deptOk = deptFilter === 'all' || (e.department ?? 'Unknown') === deptFilter;
    const tierOk = tierFilter === 'all' || e.tier === tierFilter;
    return deptOk && tierOk;
  });

  const depts = [...new Set(employees.map((e) => e.department ?? 'Unknown'))];

  function exportCSV() {
    const rows = [
      ['Name', 'Department', 'Score', 'Tier', 'Top Factor'],
      ...filtered.map((e) => [e.name, e.department ?? '', e.score.toFixed(0), e.tier, e.top_factor]),
    ];
    const csv = rows.map((r) => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = 'attrition_risk.csv'; a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-4">
      {/* Summary cards */}
      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-20" />)}
        </div>
      ) : overview && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Low Risk',      val: overview.low_count,      color: 'text-green-600',  bg: 'bg-green-50'  },
            { label: 'Medium Risk',   val: overview.medium_count,   color: 'text-amber-600',  bg: 'bg-amber-50'  },
            { label: 'High Risk',     val: overview.high_count,     color: 'text-orange-600', bg: 'bg-orange-50' },
            { label: 'Critical Risk', val: overview.critical_count, color: 'text-red-600',    bg: 'bg-red-50'    },
          ].map((item) => (
            <Card key={item.label} className={cn('border-0', item.bg)}>
              <CardContent className="p-4">
                <p className={cn('text-2xl font-bold', item.color)}>{item.val}</p>
                <p className="text-xs text-slate-500 mt-0.5">{item.label}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Chart */}
      {deptChartData.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Risk Distribution by Department</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={deptChartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="dept" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                {['Low', 'Medium', 'High', 'Critical'].map((tier) => (
                  <Bar key={tier} dataKey={tier} stackId="a" fill={TIER_COLORS[tier]} name={tier} radius={tier === 'Critical' ? [4, 4, 0, 0] : [0, 0, 0, 0]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Filters + actions */}
      <div className="flex flex-wrap items-center gap-2">
        <Filter className="h-4 w-4 text-slate-400" />
        <Select value={deptFilter} onValueChange={setDeptFilter}>
          <SelectTrigger className="w-40 h-8 text-xs"><SelectValue placeholder="All Departments" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Departments</SelectItem>
            {depts.map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={tierFilter} onValueChange={setTierFilter}>
          <SelectTrigger className="w-32 h-8 text-xs"><SelectValue placeholder="All Tiers" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Tiers</SelectItem>
            {['Low', 'Medium', 'High', 'Critical'].map((t) => (
              <SelectItem key={t} value={t}>{t}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="flex-1" />
        <Button
          variant="outline" size="sm" className="h-8 gap-1.5 text-xs"
          onClick={() => bulkMutation.mutate()}
          disabled={bulkMutation.isPending}
        >
          <Brain className="h-3.5 w-3.5" />
          {bulkMutation.isPending ? 'Queued…' : 'Run Bulk Prediction'}
        </Button>
        <Button
          variant="outline" size="sm" className="h-8 gap-1.5 text-xs"
          onClick={() => void refetch()}
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </Button>
        <Button
          variant="outline" size="sm" className="h-8 gap-1.5 text-xs"
          onClick={exportCSV}
          disabled={filtered.length === 0}
        >
          <Download className="h-3.5 w-3.5" />
          Export CSV
        </Button>
      </div>

      {/* Table */}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="text-left text-xs font-medium text-slate-500 px-4 py-2.5">Employee</th>
                <th className="text-left text-xs font-medium text-slate-500 px-4 py-2.5">Department</th>
                <th className="text-left text-xs font-medium text-slate-500 px-4 py-2.5">Score</th>
                <th className="text-left text-xs font-medium text-slate-500 px-4 py-2.5">Tier</th>
                <th className="text-left text-xs font-medium text-slate-500 px-4 py-2.5">Top Risk Factor</th>
                <th className="text-left text-xs font-medium text-slate-500 px-4 py-2.5">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-slate-50">
                    <td colSpan={6} className="px-4 py-2.5"><Skeleton className="h-4 w-full" /></td>
                  </tr>
                ))
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-10 text-slate-400 text-xs">
                    No at-risk employees found.
                  </td>
                </tr>
              ) : (
                filtered.map((emp) => (
                  <tr
                    key={emp.id}
                    className={cn(
                      'border-b border-slate-50 hover:bg-slate-50 transition-colors',
                      emp.tier === 'Critical' && 'bg-red-50/30',
                      emp.tier === 'High'     && 'bg-orange-50/20',
                    )}
                  >
                    <td className="px-4 py-2.5">
                      <p className="font-medium text-slate-700">{emp.name}</p>
                    </td>
                    <td className="px-4 py-2.5 text-slate-500 text-xs">{emp.department ?? '—'}</td>
                    <td className="px-4 py-2.5">
                      <span className="font-bold text-slate-700">{emp.score.toFixed(0)}</span>
                      <span className="text-slate-400 text-xs">/100</span>
                    </td>
                    <td className="px-4 py-2.5">
                      <Badge className={cn('text-[11px] px-2', TIER_BADGE[emp.tier])}>
                        {emp.tier}
                      </Badge>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-slate-500 max-w-[200px] truncate">
                      {emp.top_factor}
                    </td>
                    <td className="px-4 py-2.5">
                      <Button
                        variant="ghost" size="sm"
                        className="h-7 text-xs text-hrms-600 px-2"
                        onClick={() => router.push(`/employees/${emp.id}`)}
                      >
                        View Profile
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

// ─── Tab 2: Performance Predictions ──────────────────────────────────────────

function PerformanceTab() {
  const router = useRouter();
  const [bandFilter, setBandFilter] = useState('all');

  // Performance tab uses the anomalies/insights as proxy since we don't have a
  // team-wide performance endpoint without a specific manager ID.
  // We show a placeholder with instructions to select an employee.
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Filter className="h-4 w-4 text-slate-400" />
        <Select value={bandFilter} onValueChange={setBandFilter}>
          <SelectTrigger className="w-40 h-8 text-xs"><SelectValue placeholder="All Bands" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Bands</SelectItem>
            {['High', 'Medium', 'Low'].map((b) => <SelectItem key={b} value={b}>{b}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardContent className="py-12 flex flex-col items-center justify-center gap-3 text-center">
          <Brain className="h-12 w-12 text-slate-200" />
          <div>
            <p className="text-sm font-medium text-slate-600">Individual Performance Predictions</p>
            <p className="text-xs text-slate-400 mt-1 max-w-sm">
              Performance predictions are available per employee. Open an employee profile
              and navigate to the "AI Insights" tab to view their predicted performance band,
              confidence score, and improvement recommendations.
            </p>
          </div>
          <Button
            size="sm"
            className="bg-hrms-600 hover:bg-hrms-700 text-white gap-1.5 mt-2"
            onClick={() => router.push('/employees')}
          >
            <Users className="h-3.5 w-3.5" />
            Browse Employees
          </Button>
        </CardContent>
      </Card>

      {/* Band legend */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { band: 'High',   desc: 'Score ≥ 4.0',    color: 'bg-green-50 border-green-200 text-green-700' },
          { band: 'Medium', desc: 'Score 2.5 – 3.9', color: 'bg-amber-50 border-amber-200 text-amber-700' },
          { band: 'Low',    desc: 'Score < 2.5',     color: 'bg-red-50 border-red-200 text-red-700' },
        ].map((item) => (
          <Card key={item.band} className={cn('border', item.color)}>
            <CardContent className="p-3">
              <p className="text-sm font-semibold">{item.band} Performance</p>
              <p className="text-xs mt-0.5 opacity-80">{item.desc}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ─── Tab 3: Anomalies ────────────────────────────────────────────────────────

function AnomaliesTab() {
  const [sevFilter, setSevFilter] = useState<string>('all');
  const [reviewed, setReviewed]   = useState<Set<string>>(new Set());

  const { data: anomalies, isLoading, refetch } = useAnomalies();

  const filtered = (anomalies ?? []).filter((a: Anomaly) =>
    sevFilter === 'all' || a.severity === sevFilter,
  ).filter((a: Anomaly) => !reviewed.has(a.id));

  function markReviewed(id: string) {
    setReviewed((prev) => new Set([...prev, id]));
  }

  return (
    <div className="space-y-4">
      {/* Summary badges */}
      {!isLoading && anomalies && (
        <div className="flex flex-wrap gap-2">
          {(['high', 'medium', 'low'] as AnomalySeverity[]).map((sev) => {
            const count = anomalies.filter((a: Anomaly) => a.severity === sev).length;
            const cfg = SEV_CONFIG[sev];
            return (
              <div key={sev} className={cn('flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium', cfg.bg, cfg.color)}>
                <cfg.icon className="h-3.5 w-3.5" />
                {count} {cfg.label} severity
              </div>
            );
          })}
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-2">
        <Filter className="h-4 w-4 text-slate-400" />
        <Select value={sevFilter} onValueChange={setSevFilter}>
          <SelectTrigger className="w-40 h-8 text-xs"><SelectValue placeholder="All Severities" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Severities</SelectItem>
            <SelectItem value="high">High</SelectItem>
            <SelectItem value="medium">Medium</SelectItem>
            <SelectItem value="low">Low</SelectItem>
          </SelectContent>
        </Select>
        <div className="flex-1" />
        <Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs" onClick={() => refetch()}>
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </Button>
      </div>

      {/* Anomaly list */}
      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-20 w-full" />)}
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <CheckCircle2 className="h-12 w-12 text-green-300 mx-auto mb-3" />
            <p className="text-sm text-green-600 font-medium">All clear! No anomalies detected.</p>
            <p className="text-xs text-slate-400 mt-1">
              {reviewed.size > 0 ? `${reviewed.size} anomaly(ies) marked as reviewed.` : 'The system is running normally.'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {filtered.map((anomaly: Anomaly) => {
            const cfg = SEV_CONFIG[anomaly.severity] ?? SEV_CONFIG.low;
            const Icon = cfg.icon;
            return (
              <Card key={anomaly.id} className={cn('border-0', cfg.bg)}>
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <Icon className={cn('h-5 w-5 shrink-0 mt-0.5', cfg.color)} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-sm font-medium text-slate-700">{anomaly.description}</p>
                        <Badge className={cn('text-[10px] px-1.5 shrink-0', cfg.bg, cfg.color, 'border border-current/20')}>
                          {cfg.label}
                        </Badge>
                      </div>
                      <p className="text-xs text-slate-500 mt-1">{anomaly.recommended_action}</p>
                      {anomaly.affected_entities.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {anomaly.affected_entities.slice(0, 4).map((e, i) => (
                            <span key={i} className="text-[10px] bg-white/60 rounded px-1.5 py-0.5 text-slate-500">
                              {e}
                            </span>
                          ))}
                          {anomaly.affected_entities.length > 4 && (
                            <span className="text-[10px] text-slate-400">+{anomaly.affected_entities.length - 4} more</span>
                          )}
                        </div>
                      )}
                      <p className="text-[10px] text-slate-400 mt-2">
                        Detected {new Date(anomaly.detected_at).toLocaleString()}
                      </p>
                    </div>
                    <Button
                      variant="outline" size="sm"
                      className="h-7 text-xs shrink-0 bg-white/80 hover:bg-white"
                      onClick={() => markReviewed(anomaly.id)}
                    >
                      Mark reviewed
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Tab 4: Chatbot Logs (HR only) ───────────────────────────────────────────

const SAMPLE_QUESTIONS = [
  { question: 'What is my leave balance?',         count: 42, category: 'Leave'    },
  { question: 'Show my latest payslip',             count: 38, category: 'Payroll'  },
  { question: 'What is the overtime policy?',       count: 27, category: 'Policy'   },
  { question: 'How many days off do I have left?',  count: 24, category: 'Leave'    },
  { question: 'Calculate my income tax',            count: 19, category: 'Tax'      },
  { question: 'When is my attendance today?',       count: 15, category: 'Attendance'},
  { question: 'What is EOBI contribution?',         count: 12, category: 'Policy'   },
  { question: 'How to apply for annual leave?',     count: 10, category: 'HR Proc.' },
];

const CATEGORY_COLORS: Record<string, string> = {
  Leave:      'bg-blue-100 text-blue-700',
  Payroll:    'bg-green-100 text-green-700',
  Policy:     'bg-purple-100 text-purple-700',
  Tax:        'bg-amber-100 text-amber-700',
  Attendance: 'bg-slate-100 text-slate-600',
  'HR Proc.': 'bg-pink-100 text-pink-700',
};

function ChatbotLogsTab() {
  const maxCount = Math.max(...SAMPLE_QUESTIONS.map((q) => q.count));

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <Card className="bg-hrms-50 border-hrms-200">
          <CardContent className="p-4">
            <p className="text-2xl font-bold text-hrms-700">187</p>
            <p className="text-xs text-slate-500 mt-0.5">Total queries this month</p>
          </CardContent>
        </Card>
        <Card className="bg-green-50 border-green-200">
          <CardContent className="p-4">
            <p className="text-2xl font-bold text-green-700">94%</p>
            <p className="text-xs text-slate-500 mt-0.5">Queries answered confidently</p>
          </CardContent>
        </Card>
        <Card className="bg-amber-50 border-amber-200">
          <CardContent className="p-4">
            <p className="text-2xl font-bold text-amber-700">11</p>
            <p className="text-xs text-slate-500 mt-0.5">Low-confidence responses</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-hrms-600" />
            Most Asked Questions
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2.5">
          {SAMPLE_QUESTIONS.map((q, i) => (
            <div key={i}>
              <div className="flex items-center justify-between mb-0.5">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-xs text-slate-400 w-4 shrink-0">{i + 1}.</span>
                  <span className="text-xs text-slate-700 truncate">{q.question}</span>
                  <Badge className={cn('text-[10px] shrink-0', CATEGORY_COLORS[q.category] ?? 'bg-slate-100 text-slate-600')}>
                    {q.category}
                  </Badge>
                </div>
                <span className="text-xs font-bold text-slate-500 shrink-0 ml-2">{q.count}</span>
              </div>
              <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden ml-6">
                <div
                  className="h-full bg-hrms-400 rounded-full"
                  style={{ width: `${(q.count / maxCount) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            Low Confidence Queries
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[
              { q: 'What is the policy on maternity leave extension?', conf: 45, date: '2 days ago' },
              { q: 'Can I carry forward unused sick leaves?',          conf: 52, date: '3 days ago' },
              { q: 'How to dispute payroll deductions?',               conf: 38, date: '5 days ago' },
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-3 py-2 border-b border-slate-50 last:border-0">
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-slate-600">{item.q}</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">{item.date}</p>
                </div>
                <div className="shrink-0 text-right">
                  <Badge className="bg-amber-50 text-amber-700 text-[10px]">
                    {item.conf}% confidence
                  </Badge>
                </div>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-slate-400 mt-3 text-center">
            Consider adding these topics to the HR knowledge base.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function AIPage() {
  const { data: insights } = useAIInsights();

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-hrms-600" />
            <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">AI Insights</h1>
            {insights && insights.high_severity > 0 && (
              <Badge className="bg-red-100 text-red-700 text-xs">
                {insights.high_severity} critical alerts
              </Badge>
            )}
          </div>
          <p className="text-sm text-slate-500 mt-0.5">
            Predictive analytics, anomaly detection, and intelligent HR insights
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          <Zap className="h-4 w-4 text-amber-400" />
          <span className="text-xs text-slate-400">AI-powered · Offline model</span>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="attrition">
        <TabsList className="bg-slate-100 p-1 rounded-xl gap-1">
          <TabsTrigger value="attrition" className="rounded-lg text-xs px-4 data-[state=active]:bg-white data-[state=active]:shadow-sm">
            <ShieldAlert className="h-3.5 w-3.5 mr-1.5" />
            Attrition Risk
          </TabsTrigger>
          <TabsTrigger value="performance" className="rounded-lg text-xs px-4 data-[state=active]:bg-white data-[state=active]:shadow-sm">
            <TrendingDown className="h-3.5 w-3.5 mr-1.5" />
            Performance
          </TabsTrigger>
          <TabsTrigger value="anomalies" className="rounded-lg text-xs px-4 data-[state=active]:bg-white data-[state=active]:shadow-sm">
            <AlertTriangle className="h-3.5 w-3.5 mr-1.5" />
            Anomalies
            {insights && insights.high_severity > 0 && (
              <span className="ml-1.5 w-4 h-4 rounded-full bg-red-500 text-white text-[9px] flex items-center justify-center">
                {insights.high_severity}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="chatbot" className="rounded-lg text-xs px-4 data-[state=active]:bg-white data-[state=active]:shadow-sm">
            <MessageSquare className="h-3.5 w-3.5 mr-1.5" />
            Chatbot Logs
          </TabsTrigger>
        </TabsList>

        <div className="mt-4">
          <TabsContent value="attrition"   className="mt-0"><AttritionTab /></TabsContent>
          <TabsContent value="performance" className="mt-0"><PerformanceTab /></TabsContent>
          <TabsContent value="anomalies"   className="mt-0"><AnomaliesTab /></TabsContent>
          <TabsContent value="chatbot"     className="mt-0"><ChatbotLogsTab /></TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
