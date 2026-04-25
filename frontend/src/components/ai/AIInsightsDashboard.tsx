'use client';

import { useRouter } from 'next/navigation';
import {
  AlertTriangle, AlertCircle, Info, RefreshCw, TrendingDown,
  ArrowRight, Zap,
} from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

import { Button }   from '@/components/ui/button';
import { Badge }    from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn }       from '@/lib/utils';

import { useAIInsights, useAttritionOverview } from '@/hooks/useAI';
import type { Anomaly } from '@/types/ai';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const SEV_CONFIG = {
  high:   { icon: AlertCircle,   color: 'text-red-500',    bg: 'bg-red-50',    label: 'High'   },
  medium: { icon: AlertTriangle, color: 'text-amber-500',  bg: 'bg-amber-50',  label: 'Medium' },
  low:    { icon: Info,          color: 'text-blue-500',   bg: 'bg-blue-50',   label: 'Low'    },
};

const TIER_COLORS: Record<string, string> = {
  Low:      '#22c55e',
  Medium:   '#f59e0b',
  High:     '#f97316',
  Critical: '#ef4444',
};

function AnomalyRow({ anomaly }: { anomaly: Anomaly }) {
  const cfg = SEV_CONFIG[anomaly.severity] ?? SEV_CONFIG.low;
  const Icon = cfg.icon;

  return (
    <div className={cn('flex items-start gap-2.5 px-3 py-2.5 rounded-lg', cfg.bg)}>
      <Icon className={cn('h-4 w-4 shrink-0 mt-0.5', cfg.color)} />
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-slate-700 leading-snug">{anomaly.description}</p>
        <p className="text-[10px] text-slate-400 mt-0.5">{anomaly.recommended_action}</p>
      </div>
      <Badge className={cn('text-[10px] shrink-0', cfg.bg, cfg.color)}>{cfg.label}</Badge>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function AIInsightsDashboard() {
  const router = useRouter();
  const { data: insights,  isLoading: iL, refetch: refetchInsights  } = useAIInsights();
  const { data: attrition, isLoading: aL, refetch: refetchAttrition } = useAttritionOverview();

  const loading = iL || aL;

  // Donut chart data
  const donutData = attrition
    ? [
        { name: 'Low',      value: attrition.low_count,      color: TIER_COLORS.Low      },
        { name: 'Medium',   value: attrition.medium_count,   color: TIER_COLORS.Medium   },
        { name: 'High',     value: attrition.high_count,     color: TIER_COLORS.High     },
        { name: 'Critical', value: attrition.critical_count, color: TIER_COLORS.Critical },
      ].filter((d) => d.value > 0)
    : [];

  function handleRefresh() {
    refetchInsights();
    refetchAttrition();
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-hrms-600" />
            <CardTitle className="text-sm">AI Insights</CardTitle>
            {insights && insights.high_severity > 0 && (
              <Badge className="bg-red-100 text-red-700 text-xs px-1.5 py-0">
                {insights.high_severity} critical
              </Badge>
            )}
          </div>
          <div className="flex gap-1">
            <Button
              variant="ghost" size="icon"
              className="h-7 w-7 text-slate-400"
              onClick={handleRefresh}
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost" size="sm"
              className="h-7 text-xs text-hrms-600 px-2 gap-1"
              onClick={() => router.push('/ai')}
            >
              Full Report <ArrowRight className="h-3 w-3" />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
          </div>
        ) : (
          <>
            {/* Anomalies */}
            {(insights?.anomalies.length ?? 0) > 0 ? (
              <div className="space-y-1.5">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
                  Detected Anomalies
                </p>
                {(insights?.anomalies.slice(0, 3) ?? []).map((a) => (
                  <AnomalyRow key={a.id} anomaly={a} />
                ))}
                {(insights?.anomaly_count ?? 0) > 3 && (
                  <p className="text-xs text-slate-400 text-center">
                    +{(insights?.anomaly_count ?? 0) - 3} more anomalies
                  </p>
                )}
              </div>
            ) : (
              <div className="text-center py-2 text-xs text-green-600 bg-green-50 rounded-lg">
                ✓ No anomalies detected
              </div>
            )}

            {/* Attrition donut + top at-risk */}
            {attrition && attrition.total > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
                  Attrition Risk Distribution
                </p>
                <div className="flex items-center gap-3">
                  {donutData.length > 0 ? (
                    <PieChart width={80} height={80}>
                      <Pie
                        data={donutData}
                        cx={36} cy={36}
                        innerRadius={22}
                        outerRadius={36}
                        dataKey="value"
                        strokeWidth={0}
                      >
                        {donutData.map((d, i) => (
                          <Cell key={i} fill={d.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{ fontSize: 11, borderRadius: 6 }}
                        formatter={(v: number, name: string) => [v, name]}
                      />
                    </PieChart>
                  ) : null}
                  <div className="flex-1 grid grid-cols-2 gap-x-3 gap-y-0.5">
                    {[
                      { label: 'Low',      val: attrition.low_count,      color: 'text-green-600' },
                      { label: 'Medium',   val: attrition.medium_count,   color: 'text-amber-600' },
                      { label: 'High',     val: attrition.high_count,     color: 'text-orange-600' },
                      { label: 'Critical', val: attrition.critical_count, color: 'text-red-600' },
                    ].map((item) => (
                      <div key={item.label} className="flex items-center justify-between">
                        <span className="text-[11px] text-slate-500">{item.label}</span>
                        <span className={cn('text-xs font-bold', item.color)}>{item.val}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Top 3 at-risk employees */}
                {attrition.high_risk_employees.length > 0 && (
                  <div className="space-y-1">
                    <p className="text-[11px] text-slate-400 font-medium">Top At-Risk Employees</p>
                    {attrition.high_risk_employees.slice(0, 3).map((emp) => (
                      <div
                        key={emp.id}
                        className="flex items-center justify-between py-1 border-b border-slate-50 last:border-0 cursor-pointer hover:bg-slate-50 rounded px-1"
                        onClick={() => router.push(`/employees/${emp.id}`)}
                      >
                        <div className="min-w-0">
                          <p className="text-xs font-medium text-slate-700 truncate">{emp.name}</p>
                          <p className="text-[10px] text-slate-400 truncate">{emp.top_factor}</p>
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0 ml-2">
                          <span className="text-xs font-bold text-slate-600">{emp.score.toFixed(0)}</span>
                          <Badge
                            className={cn(
                              'text-[10px] px-1',
                              emp.tier === 'Critical' ? 'bg-red-100 text-red-700' :
                              emp.tier === 'High'     ? 'bg-orange-100 text-orange-700' :
                              'bg-amber-100 text-amber-700',
                            )}
                          >
                            {emp.tier}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
