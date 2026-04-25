'use client';

import { useState, useCallback } from 'react';
import {
  Bot, Cpu, CalendarClock, FileText, Users, MessageSquare,
  RefreshCw, Play, CheckCircle2, XCircle, AlertTriangle,
  Clock, Zap, Activity, Filter, ChevronRight, Loader2,
  Database, BarChart3, Calendar,
} from 'lucide-react';

import { Button }   from '@/components/ui/button';
import { Badge }    from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { cn }   from '@/lib/utils';

import {
  useAgentStatus,
  useAgentLogs,
  useTriggerAttendanceReport,
  useTriggerLeaveAnomalies,
  useTriggerPayrollValidation,
  useTriggerChronicAbsentees,
} from '@/hooks/useAgents';
import type { AgentLog, AgentLogsFilter } from '@/lib/api/agents';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function statusColor(status: string) {
  if (status === 'success') return 'text-green-600';
  if (status === 'error')   return 'text-red-500';
  return 'text-amber-500';
}

function statusBg(status: string) {
  if (status === 'success') return 'bg-green-50 text-green-700 border-green-200';
  if (status === 'error')   return 'bg-red-50 text-red-700 border-red-200';
  return 'bg-amber-50 text-amber-700 border-amber-200';
}

function modeBadge(mode: 'live' | 'mock') {
  return mode === 'live'
    ? 'bg-green-100 text-green-700 border-green-200'
    : 'bg-amber-100 text-amber-700 border-amber-200';
}

function formatDuration(ms: number | null) {
  if (ms === null) return '—';
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatTime(iso: string) {
  try {
    return new Date(iso).toLocaleTimeString('en-PK', {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
  } catch { return iso; }
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString('en-PK', {
      day: '2-digit', month: 'short',
    });
  } catch { return iso; }
}

/** Compute next occurrence of day_of_month at hour:minute PKT (UTC+5). */
function nextScheduledDate(dayOfMonth: number, hourPkt: number, minutePkt = 0) {
  const now    = new Date();
  const pktOff = 5 * 60;                              // UTC+5 minutes
  const nowPkt = new Date(now.getTime() + pktOff * 60_000);

  let year  = nowPkt.getUTCFullYear();
  let month = nowPkt.getUTCMonth();

  const candidate = new Date(Date.UTC(year, month, dayOfMonth, hourPkt - 5, minutePkt));
  if (candidate <= now) {
    month++;
    if (month > 11) { month = 0; year++; }
  }
  return new Date(Date.UTC(year, month, dayOfMonth, hourPkt - 5, minutePkt));
}

function nextDailyDate(hourPkt: number) {
  const now    = new Date();
  const today  = new Date();
  today.setUTCHours(hourPkt - 5, 0, 0, 0);
  if (today <= now) today.setUTCDate(today.getUTCDate() + 1);
  return today;
}

function daysUntil(d: Date) {
  const diff = d.getTime() - Date.now();
  const days = Math.floor(diff / 86_400_000);
  const hrs  = Math.floor((diff % 86_400_000) / 3_600_000);
  if (days === 0) return `Today in ${hrs}h`;
  if (days === 1) return `Tomorrow`;
  return `In ${days} days`;
}

// ─── Agent card definitions ────────────────────────────────────────────────────

interface AgentCardDef {
  key:         string;
  label:       string;
  description: string;
  icon:        React.ElementType;
  color:       string;
}

const AGENT_CARDS: AgentCardDef[] = [
  {
    key:         'openclaw',
    label:       'OpenClaw',
    description: 'Claude API connection layer',
    icon:        Zap,
    color:       'text-purple-500',
  },
  {
    key:         'paperclip',
    label:       'Paperclip',
    description: 'Orchestrator — routes all tasks',
    icon:        Cpu,
    color:       'text-blue-500',
  },
  {
    key:         'leave',
    label:       'Leave Agent',
    description: 'Leave analysis & anomaly detection',
    icon:        CalendarClock,
    color:       'text-emerald-500',
  },
  {
    key:         'payroll',
    label:       'Payroll Agent',
    description: 'FBR / EOBI validation & summaries',
    icon:        FileText,
    color:       'text-orange-500',
  },
  {
    key:         'attendance',
    label:       'Attendance Agent',
    description: 'Daily reports & absentee detection',
    icon:        Users,
    color:       'text-cyan-500',
  },
  {
    key:         'chatbot',
    label:       'Chatbot Agent',
    description: 'Claude-powered HR assistant',
    icon:        MessageSquare,
    color:       'text-pink-500',
  },
];

// ─── Tab 1: Status ────────────────────────────────────────────────────────────

function StatusTab() {
  const { data, isLoading, refetch, isFetching } = useAgentStatus();

  const mode        = data?.openclaw.mode ?? 'mock';
  const apiKeySet   = data?.openclaw.api_key_set ?? false;
  const agentsMap   = data?.agents ?? {};
  const dbStats     = data?.logs.db_stats ?? {};
  const redisCount  = data?.logs.redis_count ?? 0;

  function getAgentStatus(key: string) {
    if (key === 'openclaw')  return apiKeySet ? 'live' : 'mock';
    if (key === 'paperclip') return 'live';  // always available
    return agentsMap[key]?.available ? 'live' : 'mock';
  }

  function getAgentActions(key: string): string[] {
    if (key === 'openclaw' || key === 'paperclip') return [];
    return agentsMap[key]?.actions ?? [];
  }

  return (
    <div className="space-y-4">
      {/* OpenClaw banner */}
      {!isLoading && (
        <div className={cn(
          'flex items-center gap-3 rounded-xl border px-4 py-3',
          apiKeySet
            ? 'bg-green-50 border-green-200'
            : 'bg-amber-50 border-amber-200',
        )}>
          <div className={cn(
            'w-2.5 h-2.5 rounded-full shrink-0',
            apiKeySet ? 'bg-green-500 animate-pulse' : 'bg-amber-400',
          )} />
          <div className="flex-1 min-w-0">
            <p className={cn('text-sm font-semibold', apiKeySet ? 'text-green-800' : 'text-amber-800')}>
              {apiKeySet
                ? `OpenClaw connected — ${data?.openclaw.model}`
                : 'OpenClaw in mock mode — ANTHROPIC_API_KEY not set'}
            </p>
            <p className={cn('text-xs mt-0.5', apiKeySet ? 'text-green-600' : 'text-amber-600')}>
              {apiKeySet
                ? `Max tokens: ${data?.openclaw.max_tokens?.toLocaleString()} · All agents using live Claude API`
                : data?.openclaw.hint ?? 'Set ANTHROPIC_API_KEY to enable real AI responses'}
            </p>
          </div>
          <Badge className={cn('shrink-0 border', modeBadge(mode))}>
            {mode === 'live' ? '● LIVE' : '○ MOCK'}
          </Badge>
        </div>
      )}

      {/* Agent cards grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {isLoading
          ? Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-36 rounded-xl" />
            ))
          : AGENT_CARDS.map((card) => {
              const agentStatus = getAgentStatus(card.key);
              const actions     = getAgentActions(card.key);
              const Icon        = card.icon;

              const totalSuccess = Object.values(dbStats[card.key] ?? {}).reduce(
                (acc, v) => acc + (v as number), 0
              );

              return (
                <Card
                  key={card.key}
                  className={cn(
                    'relative overflow-hidden border transition-shadow hover:shadow-md',
                    agentStatus === 'live'  && 'border-green-200',
                    agentStatus === 'mock'  && 'border-amber-200',
                    agentStatus === 'error' && 'border-red-200',
                  )}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-2">
                      <div className={cn('p-2 rounded-lg bg-slate-50', card.color)}>
                        <Icon className="h-4 w-4" />
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className={cn(
                          'w-2 h-2 rounded-full',
                          agentStatus === 'live'  && 'bg-green-500',
                          agentStatus === 'mock'  && 'bg-amber-400',
                          agentStatus === 'error' && 'bg-red-500',
                        )} />
                        <span className={cn(
                          'text-[10px] font-semibold uppercase tracking-wide',
                          agentStatus === 'live'  && 'text-green-600',
                          agentStatus === 'mock'  && 'text-amber-600',
                          agentStatus === 'error' && 'text-red-600',
                        )}>
                          {agentStatus}
                        </span>
                      </div>
                    </div>

                    <p className="text-sm font-semibold text-slate-800 mt-1">{card.label}</p>
                    <p className="text-[11px] text-slate-500 mt-0.5">{card.description}</p>

                    {actions.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2.5">
                        {actions.slice(0, 3).map((a) => (
                          <span
                            key={a}
                            className="text-[10px] bg-slate-100 text-slate-500 rounded px-1.5 py-0.5"
                          >
                            {a}
                          </span>
                        ))}
                        {actions.length > 3 && (
                          <span className="text-[10px] text-slate-400">+{actions.length - 3}</span>
                        )}
                      </div>
                    )}

                    {totalSuccess > 0 && (
                      <p className="text-[10px] text-slate-400 mt-2">
                        {totalSuccess} executions total
                      </p>
                    )}
                  </CardContent>
                </Card>
              );
            })}
      </div>

      {/* Stats row */}
      {!isLoading && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Redis Logs',    value: redisCount,   icon: Database,   color: 'text-blue-500'  },
            { label: 'Total Success', value: Object.values(dbStats).reduce((a, d) => a + (d['success'] ?? 0), 0), icon: CheckCircle2, color: 'text-green-500' },
            { label: 'Total Errors',  value: Object.values(dbStats).reduce((a, d) => a + (d['error']   ?? 0), 0), icon: XCircle,      color: 'text-red-500'   },
            { label: 'Agent Mode',    value: mode === 'live' ? 'Claude Live' : 'Mock Mode', icon: Zap, color: mode === 'live' ? 'text-green-500' : 'text-amber-500' },
          ].map((stat) => (
            <Card key={stat.label} className="border-0 bg-slate-50">
              <CardContent className="p-3 flex items-center gap-3">
                <stat.icon className={cn('h-5 w-5 shrink-0', stat.color)} />
                <div>
                  <p className="text-sm font-bold text-slate-800">{stat.value}</p>
                  <p className="text-[10px] text-slate-500">{stat.label}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <div className="flex justify-end">
        <Button
          variant="outline" size="sm"
          className="h-8 gap-1.5 text-xs"
          onClick={() => void refetch()}
          disabled={isFetching}
        >
          <RefreshCw className={cn('h-3.5 w-3.5', isFetching && 'animate-spin')} />
          Refresh
        </Button>
      </div>
    </div>
  );
}

// ─── Tab 2: Logs ──────────────────────────────────────────────────────────────

function LogsTab() {
  const [filter, setFilter] = useState<AgentLogsFilter>({ limit: 25, offset: 0 });

  const { data, isLoading, isFetching, refetch } = useAgentLogs(filter);

  const logs  = data?.logs  ?? [];
  const total = data?.total ?? 0;

  function ResultCell({ log }: { log: AgentLog }) {
    const res = log.result;
    if (!res) return <span className="text-slate-400 text-xs">—</span>;

    const rec   = (res as Record<string, unknown>).recommendation as string | undefined;
    const risk  = (res as Record<string, unknown>).total_risk_score as number | undefined;
    const rate  = (res as Record<string, unknown>).attendance_rate  as number | undefined;
    const count = (res as Record<string, unknown>).count            as number | undefined;

    if (rec) {
      return (
        <Badge className={cn(
          'text-[10px] border',
          rec === 'approve' && 'bg-green-50 text-green-700 border-green-200',
          rec === 'hold'    && 'bg-amber-50 text-amber-700 border-amber-200',
          rec === 'reject'  && 'bg-red-50   text-red-700   border-red-200',
        )}>
          {rec}
          {risk !== undefined && ` · ${risk}/100`}
        </Badge>
      );
    }
    if (rate !== undefined) return <span className="text-xs text-slate-600">{(rate * 100).toFixed(1)}% attendance</span>;
    if (count !== undefined) return <span className="text-xs text-slate-600">{count} items</span>;

    const keys = Object.keys(res).slice(0, 2);
    return (
      <span className="text-[10px] text-slate-400">
        {keys.map((k) => `${k}=${String(res[k]).slice(0, 10)}`).join(', ')}
      </span>
    );
  }

  return (
    <div className="space-y-3">
      {/* Filters row */}
      <div className="flex flex-wrap items-center gap-2">
        <Filter className="h-4 w-4 text-slate-400 shrink-0" />

        <Select
          value={filter.domain ?? 'all'}
          onValueChange={(v) => setFilter((f) => ({ ...f, domain: v === 'all' ? undefined : v, offset: 0 }))}
        >
          <SelectTrigger className="w-36 h-8 text-xs">
            <SelectValue placeholder="All Domains" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Domains</SelectItem>
            {['leave', 'payroll', 'attendance', 'chatbot'].map((d) => (
              <SelectItem key={d} value={d} className="capitalize">{d}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={filter.status ?? 'all'}
          onValueChange={(v) => setFilter((f) => ({ ...f, status: v === 'all' ? undefined : v, offset: 0 }))}
        >
          <SelectTrigger className="w-32 h-8 text-xs">
            <SelectValue placeholder="All Statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="success">Success</SelectItem>
            <SelectItem value="error">Error</SelectItem>
            <SelectItem value="skipped">Skipped</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={filter.triggered_by ?? 'all'}
          onValueChange={(v) => setFilter((f) => ({ ...f, triggered_by: v === 'all' ? undefined : v, offset: 0 }))}
        >
          <SelectTrigger className="w-36 h-8 text-xs">
            <SelectValue placeholder="All Triggers" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Triggers</SelectItem>
            <SelectItem value="api_trigger">API Trigger</SelectItem>
            <SelectItem value="scheduler">Scheduler</SelectItem>
            <SelectItem value="webhook">Webhook</SelectItem>
            <SelectItem value="manual">Manual</SelectItem>
          </SelectContent>
        </Select>

        <Input
          type="date"
          className="w-36 h-8 text-xs"
          placeholder="From date"
          onChange={(e) => setFilter((f) => ({ ...f, date_from: e.target.value || undefined, offset: 0 }))}
        />
        <Input
          type="date"
          className="w-36 h-8 text-xs"
          placeholder="To date"
          onChange={(e) => setFilter((f) => ({ ...f, date_to: e.target.value || undefined, offset: 0 }))}
        />

        <div className="flex-1" />

        <p className="text-[11px] text-slate-400">{total} total · auto-refresh 30s</p>

        <Button
          variant="outline" size="sm"
          className="h-8 gap-1.5 text-xs"
          onClick={() => void refetch()}
          disabled={isFetching}
        >
          <RefreshCw className={cn('h-3.5 w-3.5', isFetching && 'animate-spin')} />
          Refresh
        </Button>
      </div>

      {/* Table */}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                {['Date', 'Time', 'Agent', 'Domain', 'Action', 'Status', 'Duration', 'Result', 'By'].map((h) => (
                  <th key={h} className="text-left text-[11px] font-medium text-slate-500 px-3 py-2.5 whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i} className="border-b border-slate-50">
                    <td colSpan={9} className="px-3 py-2">
                      <Skeleton className="h-4 w-full" />
                    </td>
                  </tr>
                ))
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={9} className="text-center py-12 text-slate-400 text-xs">
                    <Activity className="h-8 w-8 mx-auto mb-2 text-slate-200" />
                    No agent executions yet. Use the Triggers tab to run your first agent.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr
                    key={log.task_id}
                    className="border-b border-slate-50 hover:bg-slate-50/60 transition-colors"
                  >
                    <td className="px-3 py-2 text-xs text-slate-400 whitespace-nowrap">
                      {formatDate(log.created_at)}
                    </td>
                    <td className="px-3 py-2 text-xs text-slate-500 whitespace-nowrap font-mono">
                      {formatTime(log.created_at)}
                    </td>
                    <td className="px-3 py-2 text-xs text-slate-700 font-medium whitespace-nowrap">
                      {log.agent_name}
                    </td>
                    <td className="px-3 py-2">
                      <Badge className="text-[10px] bg-slate-100 text-slate-600 border-0 capitalize">
                        {log.domain}
                      </Badge>
                    </td>
                    <td className="px-3 py-2 text-xs text-slate-500 whitespace-nowrap">
                      {log.action}
                    </td>
                    <td className="px-3 py-2">
                      <span className={cn('flex items-center gap-1 text-[11px] font-medium', statusColor(log.status))}>
                        {log.status === 'success' && <CheckCircle2 className="h-3 w-3" />}
                        {log.status === 'error'   && <XCircle      className="h-3 w-3" />}
                        {log.status === 'skipped' && <AlertTriangle className="h-3 w-3" />}
                        {log.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-xs text-slate-400 font-mono whitespace-nowrap">
                      {formatDuration(log.duration_ms)}
                    </td>
                    <td className="px-3 py-2 max-w-[180px]">
                      <ResultCell log={log} />
                    </td>
                    <td className="px-3 py-2 text-[10px] text-slate-400 whitespace-nowrap capitalize">
                      {log.triggered_by?.replace('_', ' ')}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {total > (filter.limit ?? 25) && (
          <div className="flex items-center justify-between px-4 py-2.5 border-t border-slate-100">
            <p className="text-xs text-slate-400">
              {(filter.offset ?? 0) + 1}–{Math.min((filter.offset ?? 0) + (filter.limit ?? 25), total)} of {total}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline" size="sm" className="h-7 text-xs"
                disabled={(filter.offset ?? 0) === 0}
                onClick={() => setFilter((f) => ({ ...f, offset: Math.max(0, (f.offset ?? 0) - (f.limit ?? 25)) }))}
              >
                Prev
              </Button>
              <Button
                variant="outline" size="sm" className="h-7 text-xs"
                disabled={(filter.offset ?? 0) + (filter.limit ?? 25) >= total}
                onClick={() => setFilter((f) => ({ ...f, offset: (f.offset ?? 0) + (f.limit ?? 25) }))}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

// ─── Tab 3: Triggers ──────────────────────────────────────────────────────────

function TriggersTab() {
  const attendanceMutation   = useTriggerAttendanceReport();
  const leaveAnomalies       = useTriggerLeaveAnomalies();
  const absenteesMutation    = useTriggerChronicAbsentees();
  const payrollMutation      = useTriggerPayrollValidation();

  const [payrollRunId, setPayrollRunId] = useState('');
  const [lastResults, setLastResults]   = useState<Record<string, unknown>>({});

  function handleResult(key: string, data: unknown) {
    setLastResults((prev) => ({ ...prev, [key]: data }));
  }

  interface TriggerCardProps {
    title:       string;
    description: string;
    icon:        React.ElementType;
    color:       string;
    isPending:   boolean;
    onTrigger:   () => void;
    resultKey:   string;
    children?:   React.ReactNode;
  }

  function TriggerCard({
    title, description, icon: Icon, color,
    isPending, onTrigger, resultKey, children,
  }: TriggerCardProps) {
    const result = lastResults[resultKey] as Record<string, unknown> | undefined;

    return (
      <Card className="border hover:shadow-md transition-shadow">
        <CardContent className="p-4 space-y-3">
          <div className="flex items-center gap-3">
            <div className={cn('p-2 rounded-lg bg-slate-50', color)}>
              <Icon className="h-4 w-4" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-slate-800">{title}</p>
              <p className="text-[11px] text-slate-500">{description}</p>
            </div>
          </div>

          {children}

          <Button
            size="sm"
            className="w-full h-8 gap-2 text-xs bg-hrms-600 hover:bg-hrms-700 text-white"
            onClick={onTrigger}
            disabled={isPending}
          >
            {isPending ? (
              <><Loader2 className="h-3.5 w-3.5 animate-spin" />Running…</>
            ) : (
              <><Play className="h-3.5 w-3.5" />Run Now</>
            )}
          </Button>

          {result && (
            <div className={cn(
              'rounded-lg border p-3 text-xs space-y-1',
              statusBg((result.status ?? 'success') as string),
            )}>
              <p className="font-semibold">
                {result.status === 'success' ? '✓ Complete' : '⚠ Result'}
              </p>
              {result.result && typeof result.result === 'object' && (
                <div className="space-y-0.5 text-[11px] opacity-80">
                  {Object.entries(result.result as Record<string, unknown>)
                    .filter(([, v]) => typeof v !== 'object')
                    .slice(0, 5)
                    .map(([k, v]) => (
                      <p key={k}><span className="font-medium">{k}:</span> {String(v)}</p>
                    ))}
                </div>
              )}
              {result.duration_ms && (
                <p className="text-[10px] opacity-60">
                  {formatDuration(result.duration_ms as number)} · task {(result.task_id as string)?.slice(0, 8)}…
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl bg-slate-50 border border-slate-200 px-4 py-3 flex items-center gap-3">
        <Bot className="h-4 w-4 text-hrms-600 shrink-0" />
        <p className="text-xs text-slate-600">
          Manual triggers run agents synchronously and return results immediately.
          Scheduled triggers run automatically via Celery beat.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <TriggerCard
          title="Daily Attendance Report"
          description="Generate AI-powered attendance summary for today with insights and flags."
          icon={Users}
          color="text-cyan-500"
          isPending={attendanceMutation.isPending}
          onTrigger={() => {
            attendanceMutation.mutate(undefined, {
              onSuccess: (d) => handleResult('attendance', d),
            });
          }}
          resultKey="attendance"
        />

        <TriggerCard
          title="Detect Leave Anomalies"
          description="Scan all employees for suspicious leave patterns in the last 90 days."
          icon={CalendarClock}
          color="text-emerald-500"
          isPending={leaveAnomalies.isPending}
          onTrigger={() => {
            leaveAnomalies.mutate(undefined, {
              onSuccess: (d) => handleResult('leave_anomalies', d),
            });
          }}
          resultKey="leave_anomalies"
        />

        <TriggerCard
          title="Validate Payroll Run"
          description="Run AI validation on a payroll run — checks FBR tax, EOBI, and anomalies."
          icon={FileText}
          color="text-orange-500"
          isPending={payrollMutation.isPending}
          onTrigger={() => {
            if (!payrollRunId.trim()) return;
            payrollMutation.mutate(payrollRunId, {
              onSuccess: (d) => handleResult('payroll', d),
            });
          }}
          resultKey="payroll"
        >
          <Input
            placeholder="Payroll Run UUID…"
            value={payrollRunId}
            onChange={(e) => setPayrollRunId(e.target.value)}
            className="h-8 text-xs font-mono"
          />
        </TriggerCard>

        <TriggerCard
          title="Chronic Absentee Report"
          description="Identify employees with 5+ absences in the last 30 days."
          icon={BarChart3}
          color="text-red-500"
          isPending={absenteesMutation.isPending}
          onTrigger={() => {
            absenteesMutation.mutate(undefined, {
              onSuccess: (d) => handleResult('absentees', d),
            });
          }}
          resultKey="absentees"
        />
      </div>
    </div>
  );
}

// ─── Tab 4: Schedule ──────────────────────────────────────────────────────────

function ScheduleTab() {
  const { data } = useAgentStatus();

  const schedules = [
    {
      name:        'Daily Attendance Report',
      task:        'agents.daily_attendance_report',
      icon:        Users,
      color:       'text-cyan-500',
      bg:          'bg-cyan-50 border-cyan-200',
      description: 'Generates AI attendance summary with absence/late flags and insights',
      nextDate:    nextDailyDate(9),
      frequency:   'Daily at 09:00 AM PKT',
      active:      true,
    },
    {
      name:        'Payroll Pre-Approval Check',
      task:        'agents.payroll_pre_approval_check',
      icon:        AlertTriangle,
      color:       'text-amber-500',
      bg:          'bg-amber-50 border-amber-200',
      description: 'Early warning scan of draft payroll runs before the 25th trigger',
      nextDate:    nextScheduledDate(24, 6),
      frequency:   '24th of month at 06:00 AM PKT',
      active:      true,
    },
    {
      name:        'Monthly Payroll Trigger',
      task:        'agents.monthly_payroll_trigger',
      icon:        FileText,
      color:       'text-orange-500',
      bg:          'bg-orange-50 border-orange-200',
      description: 'Creates draft payroll run, validates with AI, notifies HR with recommendation',
      nextDate:    nextScheduledDate(25, 10),
      frequency:   '25th of month at 10:00 AM PKT',
      active:      true,
    },
  ];

  const beatSchedule = data?.beat_schedule ?? {};

  return (
    <div className="space-y-4">
      <div className="rounded-xl bg-slate-50 border border-slate-200 px-4 py-3 flex items-center gap-2">
        <CalendarClock className="h-4 w-4 text-slate-400 shrink-0" />
        <p className="text-xs text-slate-500">
          Schedules are registered in Celery beat and run automatically.
          Start the beat worker with:{' '}
          <code className="bg-slate-200 rounded px-1 text-[11px]">
            celery -A app.worker.celery_app beat --include app.triggers.scheduler
          </code>
        </p>
      </div>

      <div className="space-y-3">
        {schedules.map((sched) => {
          const Icon     = sched.icon;
          const isReg    = Object.keys(beatSchedule).some((k) => k.includes(sched.task.split('.')[1]!));
          const timeStr  = sched.nextDate.toLocaleString('en-PK', {
            weekday: 'short', month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit',
          });

          return (
            <Card key={sched.task} className={cn('border', sched.bg)}>
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <div className={cn('p-2 rounded-lg bg-white/60', sched.color)}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-semibold text-slate-800">{sched.name}</p>
                      <Badge className="text-[10px] bg-white/60 text-slate-600 border-slate-200">
                        {isReg ? '✓ Registered' : '○ Not registered'}
                      </Badge>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-0.5">{sched.description}</p>

                    <div className="flex flex-wrap items-center gap-4 mt-2.5">
                      <div className="flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5 text-slate-400" />
                        <span className="text-xs text-slate-600">{sched.frequency}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Calendar className="h-3.5 w-3.5 text-slate-400" />
                        <span className="text-xs font-medium text-slate-700">{timeStr}</span>
                        <Badge className="text-[10px] bg-white/80 text-hrms-600 border-hrms-200">
                          {daysUntil(sched.nextDate)}
                        </Badge>
                      </div>
                    </div>

                    <div className="mt-2">
                      <code className="text-[10px] bg-white/60 rounded px-1.5 py-0.5 text-slate-500 font-mono">
                        {sched.task}
                      </code>
                    </div>
                  </div>
                  <ChevronRight className="h-4 w-4 text-slate-300 shrink-0 mt-1" />
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Raw beat schedule from API */}
      {Object.keys(beatSchedule).length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Registered Beat Entries</CardTitle>
            <CardDescription className="text-xs">
              Live data from Celery beat schedule as seen by the backend
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(beatSchedule).map(([key, entry]) => (
                <div key={key} className="flex items-center justify-between py-1.5 border-b border-slate-50 last:border-0">
                  <code className="text-[11px] text-slate-600 font-mono">{key}</code>
                  <span className="text-[10px] text-slate-400 ml-4">{entry.schedule}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function AgentDashboardPage() {
  const { data, isLoading } = useAgentStatus();
  const mode    = data?.openclaw.mode ?? 'mock';
  const apiKeySet = data?.openclaw.api_key_set ?? false;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 bg-hrms-600 rounded-xl flex items-center justify-center">
              <Bot className="h-5 w-5 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">
              Agent Factory
            </h1>
            {!isLoading && (
              <Badge className={cn('border', modeBadge(mode))}>
                {mode === 'live' ? '● Claude Live' : '○ Mock Mode'}
              </Badge>
            )}
          </div>
          <p className="text-sm text-slate-500 mt-1 ml-11.5">
            AI-powered HR automation — orchestrated by Paperclip, powered by Claude
          </p>
        </div>

        {!isLoading && !apiKeySet && (
          <div className="flex items-center gap-2 text-xs bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-500 shrink-0" />
            <span className="text-amber-700">
              Set <code className="bg-amber-100 rounded px-1">ANTHROPIC_API_KEY</code> for live AI
            </span>
          </div>
        )}
      </div>

      {/* Tabs */}
      <Tabs defaultValue="status">
        <TabsList className="bg-slate-100 p-1 rounded-xl gap-1">
          {[
            { value: 'status',   label: 'Agent Status',  icon: Activity    },
            { value: 'logs',     label: 'Execution Logs', icon: FileText   },
            { value: 'triggers', label: 'Triggers',       icon: Play       },
            { value: 'schedule', label: 'Schedule',       icon: CalendarClock },
          ].map(({ value, label, icon: Icon }) => (
            <TabsTrigger
              key={value}
              value={value}
              className="rounded-lg text-xs px-4 data-[state=active]:bg-white data-[state=active]:shadow-sm"
            >
              <Icon className="h-3.5 w-3.5 mr-1.5" />
              {label}
            </TabsTrigger>
          ))}
        </TabsList>

        <div className="mt-4">
          <TabsContent value="status"   className="mt-0"><StatusTab /></TabsContent>
          <TabsContent value="logs"     className="mt-0"><LogsTab /></TabsContent>
          <TabsContent value="triggers" className="mt-0"><TriggersTab /></TabsContent>
          <TabsContent value="schedule" className="mt-0"><ScheduleTab /></TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
