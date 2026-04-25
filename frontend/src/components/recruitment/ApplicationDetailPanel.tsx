'use client';

import { useState } from 'react';
import {
  X, ExternalLink, FileText, Clock, ChevronDown, ChevronUp,
  Mail, Phone, MapPin, Linkedin, Globe, User,
} from 'lucide-react';

import { Button }   from '@/components/ui/button';
import { Badge }    from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';

import { AIScoreCard } from './AIScoreCard';
import { useApplication, useUpdateStage } from '@/hooks/useRecruitment';
import type { ApplicationStatus, StageHistoryItem, ScoringResult } from '@/types/recruitment';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<ApplicationStatus, string> = {
  applied:     'Applied',
  screening:   'Screening',
  shortlisted: 'Shortlisted',
  interview:   'Interview',
  offered:     'Offered',
  hired:       'Hired',
  rejected:    'Rejected',
  withdrawn:   'Withdrawn',
};

const STATUS_COLORS: Record<ApplicationStatus, string> = {
  applied:     'bg-slate-100 text-slate-700 border-slate-200',
  screening:   'bg-blue-50 text-blue-700 border-blue-200',
  shortlisted: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  interview:   'bg-violet-50 text-violet-700 border-violet-200',
  offered:     'bg-amber-50 text-amber-700 border-amber-200',
  hired:       'bg-green-50 text-green-700 border-green-200',
  rejected:    'bg-red-50 text-red-700 border-red-200',
  withdrawn:   'bg-slate-100 text-slate-500 border-slate-200',
};

const NEXT_STAGES: Partial<Record<ApplicationStatus, ApplicationStatus[]>> = {
  applied:     ['screening', 'shortlisted', 'rejected'],
  screening:   ['shortlisted', 'rejected'],
  shortlisted: ['interview', 'rejected'],
  interview:   ['offered', 'rejected'],
  offered:     ['hired', 'rejected'],
};

function fmt(iso: string) {
  return new Date(iso).toLocaleString('en-PK', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

// ─── Stage history timeline ───────────────────────────────────────────────────

function StageTimeline({ history }: { history: StageHistoryItem[] }) {
  return (
    <ol className="relative border-l border-slate-200 space-y-4 ml-3">
      {history.map((item, i) => (
        <li key={i} className="ml-5">
          <span className="absolute -left-2 flex h-4 w-4 items-center justify-center rounded-full bg-white border-2 border-slate-300" />
          <div className="flex flex-wrap items-baseline gap-x-2">
            <span className="text-xs font-semibold text-slate-800">
              {STATUS_LABELS[item.to_status as ApplicationStatus] ?? item.to_status}
            </span>
            {item.from_status && (
              <span className="text-xs text-slate-400">
                from {STATUS_LABELS[item.from_status as ApplicationStatus] ?? item.from_status}
              </span>
            )}
          </div>
          {item.notes && (
            <p className="text-xs text-slate-600 mt-0.5 italic">"{item.notes}"</p>
          )}
          <time className="text-xs text-slate-400">{fmt(item.changed_at)}</time>
        </li>
      ))}
    </ol>
  );
}

// ─── Move stage panel ─────────────────────────────────────────────────────────

function MoveStagePanel({
  appId,
  currentStatus,
  onMoved,
}: {
  appId:         string;
  currentStatus: ApplicationStatus;
  onMoved?:      () => void;
}) {
  const [newStatus, setNewStatus] = useState<ApplicationStatus | ''>('');
  const [notes,     setNotes]     = useState('');
  const [reason,    setReason]    = useState('');
  const updateStage               = useUpdateStage();

  const nextStages = NEXT_STAGES[currentStatus] ?? [];
  if (nextStages.length === 0) return null;

  function submit() {
    if (!newStatus) return;
    updateStage.mutate(
      {
        id:   appId,
        data: {
          new_status:        newStatus,
          notes:             notes || undefined,
          rejection_reason:  newStatus === 'rejected' ? reason : undefined,
        },
      },
      {
        onSuccess: () => {
          setNewStatus('');
          setNotes('');
          setReason('');
          onMoved?.();
        },
      },
    );
  }

  return (
    <div className="rounded-lg border border-dashed p-3 space-y-2.5">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Move Stage</p>
      <Select value={newStatus} onValueChange={(v) => setNewStatus(v as ApplicationStatus)}>
        <SelectTrigger className="h-8 text-sm">
          <SelectValue placeholder="Select next stage…" />
        </SelectTrigger>
        <SelectContent>
          {nextStages.map((s) => (
            <SelectItem key={s} value={s}>{STATUS_LABELS[s]}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      {newStatus === 'rejected' && (
        <Textarea
          rows={2}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Rejection reason (optional)"
          className="text-sm resize-none"
        />
      )}
      <Textarea
        rows={2}
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Internal notes (optional)"
        className="text-sm resize-none"
      />
      <Button
        size="sm"
        disabled={!newStatus || updateStage.isPending}
        onClick={submit}
        className="w-full"
      >
        {updateStage.isPending ? 'Moving…' : `Move to ${newStatus ? STATUS_LABELS[newStatus] : '…'}`}
      </Button>
    </div>
  );
}

// ─── Main panel ───────────────────────────────────────────────────────────────

interface Props {
  applicationId: string;
  onClose:       () => void;
  onSchedule?:   (appId: string) => void;
  onOffer?:      (appId: string) => void;
}

export function ApplicationDetailPanel({
  applicationId,
  onClose,
  onSchedule,
  onOffer,
}: Props) {
  const { data: app, isLoading } = useApplication(applicationId);
  const [showHistory, setShowHistory] = useState(false);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 text-sm">
        Loading application…
      </div>
    );
  }

  if (!app) return null;

  // Parse AI scoring data from ai_explanation JSONB
  const scoring: Partial<ScoringResult> | null = app.ai_explanation
    ? (app.ai_explanation as any)
    : null;

  const stageHistory: StageHistoryItem[] = app.stage_history ?? [];

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex items-start justify-between p-5 border-b shrink-0">
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-slate-900 truncate">
            {app.candidate_name}
          </h2>
          <p className="text-sm text-slate-500 truncate">{app.job_posting?.title ?? 'Application'}</p>
          <Badge
            variant="outline"
            className={`mt-1.5 text-xs ${STATUS_COLORS[app.status]}`}
          >
            {STATUS_LABELS[app.status]}
          </Badge>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} className="shrink-0 -mt-1 -mr-1">
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">

        {/* Contact info */}
        <div className="space-y-1.5">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Contact</p>
          <div className="space-y-1 text-sm text-slate-700">
            <a href={`mailto:${app.candidate_email}`}
              className="flex items-center gap-2 hover:text-blue-600 transition-colors">
              <Mail className="h-3.5 w-3.5 text-slate-400 shrink-0" />
              {app.candidate_email}
            </a>
            {app.candidate_phone && (
              <div className="flex items-center gap-2">
                <Phone className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                {app.candidate_phone}
              </div>
            )}
            {app.candidate_location && (
              <div className="flex items-center gap-2">
                <MapPin className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                {app.candidate_location}
              </div>
            )}
            {app.linkedin_url && (
              <a href={app.linkedin_url} target="_blank" rel="noreferrer"
                className="flex items-center gap-2 hover:text-blue-600 transition-colors">
                <Linkedin className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                LinkedIn Profile
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
            {app.portfolio_url && (
              <a href={app.portfolio_url} target="_blank" rel="noreferrer"
                className="flex items-center gap-2 hover:text-blue-600 transition-colors">
                <Globe className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                Portfolio
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        </div>

        <Separator />

        {/* Meta */}
        <div className="grid grid-cols-2 gap-y-2 text-xs">
          <span className="text-slate-500">Source</span>
          <span className="text-slate-800 font-medium capitalize">{app.source.replace('_', ' ')}</span>
          <span className="text-slate-500">Applied</span>
          <span className="text-slate-800 font-medium">
            {new Date(app.applied_at).toLocaleDateString('en-PK', { day:'2-digit', month:'short', year:'numeric' })}
          </span>
          {app.referred_by && (
            <>
              <span className="text-slate-500">Referred by</span>
              <span className="text-slate-800 font-medium flex items-center gap-1">
                <User className="h-3 w-3" />
                {app.referred_by}
              </span>
            </>
          )}
        </div>

        <Separator />

        {/* CV */}
        {app.cv_url && (
          <div className="space-y-1.5">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Resume / CV</p>
            <a
              href={app.cv_url}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 text-sm text-blue-600 hover:underline"
            >
              <FileText className="h-4 w-4 shrink-0" />
              View / Download CV
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        )}

        {/* Cover letter */}
        {app.cover_letter && (
          <div className="space-y-1.5">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Cover Letter</p>
            <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap rounded-lg bg-slate-50 p-3">
              {app.cover_letter}
            </p>
          </div>
        )}

        {/* AI Score */}
        <div className="space-y-1.5">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">AI Evaluation</p>
          <AIScoreCard
            score={app.ai_score}
            explanation={scoring?.explanation}
            skillsMatched={scoring?.skills_matched}
            skillsMissing={scoring?.skills_missing}
            skillsScore={scoring?.skills_score}
            expScore={scoring?.experience_score}
            titleScore={scoring?.title_relevance}
            eduScore={scoring?.education_score}
            biasFlags={scoring?.bias_flags}
          />
        </div>

        {/* HR Notes */}
        {app.hr_notes && (
          <div className="space-y-1.5">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">HR Notes</p>
            <p className="text-sm text-slate-700 rounded-lg bg-amber-50 border border-amber-100 p-3 leading-relaxed">
              {app.hr_notes}
            </p>
          </div>
        )}

        {/* Stage timeline */}
        {stageHistory.length > 0 && (
          <div className="space-y-2">
            <button
              type="button"
              onClick={() => setShowHistory((v) => !v)}
              className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wide hover:text-slate-800 transition-colors"
            >
              <Clock className="h-3.5 w-3.5" />
              Stage History ({stageHistory.length})
              {showHistory ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </button>
            {showHistory && <StageTimeline history={stageHistory} />}
          </div>
        )}

        {/* Move stage */}
        <MoveStagePanel appId={app.id} currentStatus={app.status} />

        {/* Action buttons */}
        <div className="space-y-2">
          {['applied', 'screening', 'shortlisted', 'interview'].includes(app.status) && onSchedule && (
            <Button
              variant="outline"
              className="w-full"
              onClick={() => onSchedule(app.id)}
            >
              Schedule Interview
            </Button>
          )}
          {app.status === 'offered' && onOffer && app.offer_letter_url && (
            <a href={app.offer_letter_url} target="_blank" rel="noreferrer">
              <Button variant="outline" className="w-full gap-2">
                <FileText className="h-4 w-4" />
                View Offer Letter
              </Button>
            </a>
          )}
          {app.status === 'shortlisted' && onOffer && (
            <Button className="w-full" onClick={() => onOffer(app.id)}>
              Generate Offer Letter
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
