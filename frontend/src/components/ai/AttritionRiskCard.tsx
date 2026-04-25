'use client';

import { RefreshCw, AlertTriangle, CheckCircle2, ShieldAlert, Skull } from 'lucide-react';

import { Button }   from '@/components/ui/button';
import { Badge }    from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn }       from '@/lib/utils';

import { useAttritionRisk } from '@/hooks/useAI';
import { useQueryClient }   from '@tanstack/react-query';
import { aiKeys }           from '@/hooks/useAI';
import * as aiApi           from '@/lib/api/ai';
import type { AttritionResult } from '@/types/ai';

// ─── Tier config ──────────────────────────────────────────────────────────────

const TIER_CONFIG = {
  Low:      { color: 'text-green-600',  bg: 'bg-green-50',  border: 'border-green-200',  icon: CheckCircle2,  label: 'Low Risk'      },
  Medium:   { color: 'text-amber-600',  bg: 'bg-amber-50',  border: 'border-amber-200',  icon: AlertTriangle, label: 'Medium Risk'   },
  High:     { color: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-200', icon: ShieldAlert,   label: 'High Risk'     },
  Critical: { color: 'text-red-600',    bg: 'bg-red-50',    border: 'border-red-200',    icon: Skull,         label: 'Critical Risk' },
} as const;

// ─── Score gauge ──────────────────────────────────────────────────────────────

function ScoreGauge({ score, tier }: { score: number; tier: string }) {
  const t = TIER_CONFIG[tier as keyof typeof TIER_CONFIG] ?? TIER_CONFIG.Low;
  const pct = score;

  const trackColor =
    tier === 'Critical' ? '#fecaca' :
    tier === 'High'     ? '#fed7aa' :
    tier === 'Medium'   ? '#fde68a' :
    '#bbf7d0';

  const fillColor =
    tier === 'Critical' ? '#dc2626' :
    tier === 'High'     ? '#ea580c' :
    tier === 'Medium'   ? '#d97706' :
    '#16a34a';

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-28 h-28">
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          <circle cx="50" cy="50" r="40" fill="none" stroke={trackColor} strokeWidth="12" />
          <circle
            cx="50" cy="50" r="40"
            fill="none"
            stroke={fillColor}
            strokeWidth="12"
            strokeDasharray={`${pct * 2.513} 251.3`}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={cn('text-2xl font-bold', t.color)}>{score.toFixed(0)}</span>
          <span className="text-[10px] text-slate-400">/ 100</span>
        </div>
      </div>
      <Badge className={cn('text-xs px-2 py-0.5', t.bg, t.color, 'border', t.border)}>
        {t.label}
      </Badge>
    </div>
  );
}

// ─── Risk factor bar ──────────────────────────────────────────────────────────

function FactorBar({ label, impact, tier }: { label: string; impact: number; tier: string }) {
  const pct = Math.min(100, impact * 100);
  const barColor =
    tier === 'Critical' ? 'bg-red-500' :
    tier === 'High'     ? 'bg-orange-500' :
    tier === 'Medium'   ? 'bg-amber-500' :
    'bg-green-500';

  return (
    <div className="space-y-0.5">
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-600 truncate">{label}</span>
        <span className="text-xs text-slate-400 ml-2">{pct.toFixed(0)}%</span>
      </div>
      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full transition-all', barColor)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

interface AttritionRiskCardProps {
  employeeId: string;
  className?: string;
}

export function AttritionRiskCard({ employeeId, className }: AttritionRiskCardProps) {
  const qc = useQueryClient();
  const { data, isLoading, isError } = useAttritionRisk(employeeId);

  async function handleRefresh() {
    await aiApi.getEmployeeAttrition(employeeId, true);   // force=true
    qc.invalidateQueries({ queryKey: aiKeys.attritionEmployee(employeeId) });
  }

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Attrition Risk</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-32 w-32 rounded-full mx-auto" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-2/3" />
        </CardContent>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card className={cn('border-slate-200', className)}>
        <CardContent className="py-8 text-center text-slate-400 text-sm">
          Unable to load attrition risk.
          <Button variant="ghost" size="sm" className="block mx-auto mt-2" onClick={handleRefresh}>
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  const t = TIER_CONFIG[data.risk_tier as keyof typeof TIER_CONFIG] ?? TIER_CONFIG.Low;

  return (
    <Card className={cn('border', t.border, className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">Attrition Risk Analysis</CardTitle>
          <Button
            variant="ghost" size="icon"
            className="h-7 w-7 text-slate-400 hover:text-slate-600"
            onClick={handleRefresh}
            title="Refresh analysis"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
        </div>
        <p className="text-xs text-slate-400">
          Confidence: {(data.confidence * 100).toFixed(0)}% · {data.model_type === 'rule_based' ? 'Rule-based model' : 'ML model'}
        </p>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Score gauge */}
        <div className="flex justify-center">
          <ScoreGauge score={data.risk_score} tier={data.risk_tier} />
        </div>

        {/* Risk factors */}
        {data.top_risk_factors.length > 0 && (
          <div className="space-y-2.5">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
              Top Risk Factors
            </p>
            {data.top_risk_factors.map((f, i) => (
              <div key={i}>
                <FactorBar
                  label={f.label || f.factor.replace(/_/g, ' ')}
                  impact={f.impact}
                  tier={data.risk_tier}
                />
                <p className="text-[10px] text-slate-400 mt-0.5 leading-snug">{f.direction}</p>
              </div>
            ))}
          </div>
        )}

        {/* Recommended actions */}
        {data.recommended_actions.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
              Recommended Actions
            </p>
            <ul className="space-y-1">
              {data.recommended_actions.map((action, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className={cn('text-xs mt-0.5', t.color)}>→</span>
                  <span className="text-xs text-slate-600 leading-snug">{action}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
