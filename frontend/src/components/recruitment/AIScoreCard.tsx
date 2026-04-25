'use client';

import { AlertTriangle } from 'lucide-react';
import { Badge }  from '@/components/ui/badge';

interface Props {
  score:          number | null;
  explanation?:   string | null;
  skillsMatched?: string[];
  skillsMissing?: string[];
  skillsScore?:   number;
  expScore?:      number;
  titleScore?:    number;
  eduScore?:      number;
  biasFlags?:     string[];
  compact?:       boolean;
}

function scoreColor(s: number | null): string {
  if (s === null) return 'text-slate-400';
  if (s >= 70) return 'text-green-600';
  if (s >= 50) return 'text-amber-500';
  return 'text-red-500';
}

function scoreBg(s: number | null): string {
  if (s === null) return 'bg-slate-100';
  if (s >= 70) return 'bg-green-50 border-green-200';
  if (s >= 50) return 'bg-amber-50 border-amber-200';
  return 'bg-red-50 border-red-200';
}

function ScoreRing({ score }: { score: number | null }) {
  const s         = score ?? 0;
  const radius    = 28;
  const circumf   = 2 * Math.PI * radius;
  const offset    = circumf - (s / 100) * circumf;
  const color     = s >= 70 ? '#16a34a' : s >= 50 ? '#d97706' : '#dc2626';

  return (
    <div className="relative inline-flex items-center justify-center w-20 h-20">
      <svg width="80" height="80" viewBox="0 0 80 80" className="-rotate-90">
        <circle cx="40" cy="40" r={radius} fill="none" stroke="#e2e8f0" strokeWidth="7" />
        <circle
          cx="40" cy="40" r={radius}
          fill="none"
          stroke={color}
          strokeWidth="7"
          strokeDasharray={circumf}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-700"
        />
      </svg>
      <span className={`absolute text-xl font-bold ${scoreColor(score)}`}>
        {score !== null ? Math.round(score) : '–'}
      </span>
    </div>
  );
}

function SubBar({ label, value, max = 40 }: { label: string; value?: number; max?: number }) {
  if (value === undefined) return null;
  const pct = (value / max) * 100;
  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-xs text-slate-600">
        <span>{label}</span>
        <span className="font-medium">{value.toFixed(0)}/{max}</span>
      </div>
      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-500 rounded-full transition-all duration-500"
          style={{ width: `${Math.min(100, pct)}%` }}
        />
      </div>
    </div>
  );
}

export function AIScoreCard({
  score, explanation, skillsMatched = [], skillsMissing = [],
  skillsScore, expScore, titleScore, eduScore,
  biasFlags = [], compact = false,
}: Props) {
  if (score === null && !explanation) {
    return (
      <div className="text-xs text-slate-400 italic py-2">AI scoring pending…</div>
    );
  }

  if (compact) {
    return (
      <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-xs font-semibold ${scoreBg(score)}`}>
        <span className={scoreColor(score)}>
          {score !== null ? `${Math.round(score)}/100` : 'Pending'}
        </span>
      </div>
    );
  }

  return (
    <div className={`rounded-xl border p-4 ${scoreBg(score)} space-y-4`}>
      {/* Score ring + explanation */}
      <div className="flex items-start gap-4">
        <ScoreRing score={score} />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">AI Match Score</p>
          {explanation && (
            <p className="text-sm text-slate-700 leading-relaxed">{explanation}</p>
          )}
        </div>
      </div>

      {/* Sub-scores */}
      {(skillsScore !== undefined || expScore !== undefined) && (
        <div className="space-y-2">
          <SubBar label="Skills Match"       value={skillsScore}  max={40} />
          <SubBar label="Experience"         value={expScore}     max={30} />
          <SubBar label="Title Relevance"    value={titleScore}   max={20} />
          <SubBar label="Education"          value={eduScore}     max={10} />
        </div>
      )}

      {/* Matched skills */}
      {skillsMatched.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-500 mb-1.5">Matched Skills</p>
          <div className="flex flex-wrap gap-1.5">
            {skillsMatched.map((s) => (
              <Badge key={s} variant="outline"
                className="bg-green-50 border-green-200 text-green-700 text-xs">
                {s}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Missing skills */}
      {skillsMissing.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-500 mb-1.5">Missing Skills</p>
          <div className="flex flex-wrap gap-1.5">
            {skillsMissing.map((s) => (
              <Badge key={s} variant="outline"
                className="bg-red-50 border-red-200 text-red-600 text-xs">
                {s}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Bias flags */}
      {biasFlags.length > 0 && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-2.5">
          <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-semibold text-amber-800">Bias Indicators Detected</p>
            <p className="text-xs text-amber-700 mt-0.5">
              CV contains: {biasFlags.join(', ')}. These are flagged for awareness and were
              <strong> not</strong> used in scoring.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
