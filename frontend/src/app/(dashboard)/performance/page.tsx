'use client';

import { useState } from 'react';
import {
  BarChart3, Target, Users, TrendingUp, Plus, Play, CheckCircle,
  ChevronRight, Star, AlertCircle, Download, RefreshCw, Eye,
} from 'lucide-react';

import { Button }    from '@/components/ui/button';
import { Badge }     from '@/components/ui/badge';
import { Progress }  from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Card, CardContent, CardDescription, CardHeader, CardTitle,
} from '@/components/ui/card';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Input }    from '@/components/ui/input';
import { Label }    from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

import {
  useCycles,
  useCreateCycle,
  useLaunchCycle,
  useCloseCycle,
  useMyAppraisal,
  useAppraisals,
  useAppraisal,
  useGoals,
  useBulkSetGoals,
  useUpdateGoal,
  useSubmitSelfReview,
  useSubmitManagerReview,
  useBellCurve,
  useTeamSummary,
  usePips,
} from '@/hooks/usePerformance';

import { reportUrl } from '@/lib/api/performance';

import type {
  AppraisalCycle,
  AppraisalCycleCreate,
  Appraisal,
  CycleStatus,
  AppraisalStatus,
  CompetencyKey,
  GoalCreate,
} from '@/types/performance';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const CYCLE_STATUS_COLORS: Record<CycleStatus, string> = {
  upcoming:        'bg-slate-100 text-slate-600 border-slate-200',
  active:          'bg-blue-50  text-blue-700  border-blue-200',
  self_review:     'bg-yellow-50 text-yellow-700 border-yellow-200',
  manager_review:  'bg-orange-50 text-orange-700 border-orange-200',
  calibration:     'bg-purple-50 text-purple-700 border-purple-200',
  completed:       'bg-green-50 text-green-700  border-green-200',
  archived:        'bg-gray-100  text-gray-500   border-gray-200',
};

const APPRAISAL_STATUS_LABELS: Record<AppraisalStatus, string> = {
  not_started:               'Not Started',
  self_review_pending:       'Self Review Pending',
  self_review_submitted:     'Self Review Done',
  manager_review_pending:    'Manager Review Pending',
  manager_review_submitted:  'Manager Review Done',
  hr_review:                 'HR Review',
  completed:                 'Completed',
};

const APPRAISAL_STATUS_COLORS: Record<AppraisalStatus, string> = {
  not_started:               'bg-slate-100 text-slate-500',
  self_review_pending:       'bg-yellow-50 text-yellow-700',
  self_review_submitted:     'bg-blue-50   text-blue-700',
  manager_review_pending:    'bg-orange-50 text-orange-700',
  manager_review_submitted:  'bg-purple-50 text-purple-700',
  hr_review:                 'bg-indigo-50 text-indigo-700',
  completed:                 'bg-green-50  text-green-700',
};

const COMPETENCIES: CompetencyKey[] = [
  'communication', 'teamwork', 'leadership', 'problem_solving', 'initiative',
];

function ratingStars(rating: number | null, max = 5) {
  if (rating === null) return <span className="text-slate-400 text-sm">—</span>;
  const pct = Math.round((rating / max) * 100);
  return (
    <div className="flex items-center gap-1">
      <div className="flex gap-0.5">
        {Array.from({ length: max }).map((_, i) => (
          <Star
            key={i}
            className={`h-3.5 w-3.5 ${
              i < Math.round(rating)
                ? 'fill-amber-400 text-amber-400'
                : 'text-slate-200 fill-slate-200'
            }`}
          />
        ))}
      </div>
      <span className="text-xs text-slate-500">{rating.toFixed(1)}</span>
    </div>
  );
}

// ─── Create Cycle Dialog ──────────────────────────────────────────────────────

function CreateCycleDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const createCycle = useCreateCycle();
  const [form, setForm] = useState<AppraisalCycleCreate>({
    name:           '',
    year:           new Date().getFullYear(),
    start_date:     '',
    end_date:       '',
    rating_scale_min: 1,
    rating_scale_max: 5,
  });

  function set(k: keyof AppraisalCycleCreate, v: unknown) {
    setForm((p) => ({ ...p, [k]: v }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await createCycle.mutateAsync(form);
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>New Appraisal Cycle</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2 space-y-1">
              <Label>Cycle Name *</Label>
              <Input
                placeholder="e.g. Annual Review 2025"
                value={form.name}
                onChange={(e) => set('name', e.target.value)}
                required
              />
            </div>
            <div className="space-y-1">
              <Label>Year *</Label>
              <Input
                type="number"
                min={2020}
                max={2099}
                value={form.year}
                onChange={(e) => set('year', Number(e.target.value))}
                required
              />
            </div>
            <div className="space-y-1">
              <Label>Quarter</Label>
              <Select onValueChange={(v) => set('quarter', v === 'none' ? null : Number(v))}>
                <SelectTrigger><SelectValue placeholder="None" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None (Annual)</SelectItem>
                  <SelectItem value="1">Q1</SelectItem>
                  <SelectItem value="2">Q2</SelectItem>
                  <SelectItem value="3">Q3</SelectItem>
                  <SelectItem value="4">Q4</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>Start Date *</Label>
              <Input
                type="date"
                value={form.start_date}
                onChange={(e) => set('start_date', e.target.value)}
                required
              />
            </div>
            <div className="space-y-1">
              <Label>End Date *</Label>
              <Input
                type="date"
                value={form.end_date}
                onChange={(e) => set('end_date', e.target.value)}
                required
              />
            </div>
            <div className="space-y-1">
              <Label>Self Review Deadline</Label>
              <Input
                type="date"
                value={form.self_review_deadline ?? ''}
                onChange={(e) => set('self_review_deadline', e.target.value || null)}
              />
            </div>
            <div className="space-y-1">
              <Label>Manager Review Deadline</Label>
              <Input
                type="date"
                value={form.manager_review_deadline ?? ''}
                onChange={(e) => set('manager_review_deadline', e.target.value || null)}
              />
            </div>
            <div className="space-y-1">
              <Label>Rating Scale Min</Label>
              <Input
                type="number"
                min={0}
                step={0.5}
                value={form.rating_scale_min ?? 1}
                onChange={(e) => set('rating_scale_min', Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label>Rating Scale Max</Label>
              <Input
                type="number"
                min={1}
                step={0.5}
                value={form.rating_scale_max ?? 5}
                onChange={(e) => set('rating_scale_max', Number(e.target.value))}
              />
            </div>
            <div className="col-span-2 space-y-1">
              <Label>Self Review Instructions</Label>
              <Textarea
                rows={2}
                placeholder="Instructions for employees…"
                value={form.self_review_instructions ?? ''}
                onChange={(e) => set('self_review_instructions', e.target.value)}
              />
            </div>
            <div className="col-span-2 space-y-1">
              <Label>Manager Review Instructions</Label>
              <Textarea
                rows={2}
                placeholder="Instructions for managers…"
                value={form.manager_review_instructions ?? ''}
                onChange={(e) => set('manager_review_instructions', e.target.value)}
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={createCycle.isPending}>
              {createCycle.isPending ? 'Creating…' : 'Create Cycle'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Cycle Card ───────────────────────────────────────────────────────────────

function CycleCard({
  cycle,
  onSelect,
}: {
  cycle: AppraisalCycle;
  onSelect: (c: AppraisalCycle) => void;
}) {
  const launchCycle = useLaunchCycle();
  const closeCycle  = useCloseCycle();

  const completed  = cycle.reviews_completed ?? 0;
  const total      = cycle.total_employees   ?? 0;
  const progress   = total > 0 ? Math.round((completed / total) * 100) : 0;

  return (
    <Card className="hover:shadow-md transition-shadow cursor-pointer" onClick={() => onSelect(cycle)}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="text-base font-semibold">{cycle.name}</CardTitle>
            <CardDescription>
              {cycle.start_date} → {cycle.end_date}
              {cycle.period_label && ` · ${cycle.period_label}`}
            </CardDescription>
          </div>
          <Badge variant="outline" className={CYCLE_STATUS_COLORS[cycle.status as CycleStatus] ?? ''}>
            {cycle.status.replace(/_/g, ' ')}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {total > 0 && (
          <div>
            <div className="flex justify-between text-xs text-slate-500 mb-1">
              <span>{completed} / {total} reviews</span>
              <span>{progress}%</span>
            </div>
            <Progress value={progress} className="h-1.5" />
          </div>
        )}
        <div className="flex gap-2 pt-1" onClick={(e) => e.stopPropagation()}>
          {cycle.status === 'upcoming' && (
            <Button
              size="sm"
              onClick={() => launchCycle.mutate(cycle.id)}
              disabled={launchCycle.isPending}
            >
              <Play className="h-3.5 w-3.5 mr-1" />
              Launch
            </Button>
          )}
          {['active', 'self_review', 'manager_review', 'calibration'].includes(cycle.status) && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => closeCycle.mutate(cycle.id)}
              disabled={closeCycle.isPending}
            >
              <CheckCircle className="h-3.5 w-3.5 mr-1" />
              Close
            </Button>
          )}
          <Button size="sm" variant="ghost" onClick={() => onSelect(cycle)}>
            <Eye className="h-3.5 w-3.5 mr-1" />
            View
          </Button>
          {cycle.status !== 'upcoming' && (
            <a href={reportUrl(cycle.id)} target="_blank" rel="noopener noreferrer">
              <Button size="sm" variant="ghost">
                <Download className="h-3.5 w-3.5 mr-1" />
                Report
              </Button>
            </a>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Bell Curve Chart ─────────────────────────────────────────────────────────

function BellCurveChart({ cycleId }: { cycleId: string }) {
  const { data, isLoading } = useBellCurve(cycleId);

  if (isLoading) return <div className="py-8 text-center text-slate-400">Loading…</div>;
  if (!data || data.total === 0) return (
    <div className="py-8 text-center text-slate-400">No completed appraisals yet.</div>
  );

  const maxCount = Math.max(...data.buckets.map((b) => b.count), 1);

  return (
    <div className="space-y-3">
      {data.is_skewed && data.skew_note && (
        <div className="flex items-center gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-700">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          {data.skew_note}
        </div>
      )}
      <div className="flex items-end gap-3 h-40 px-2">
        {data.buckets.map((b) => (
          <div key={b.rating} className="flex-1 flex flex-col items-center gap-1">
            <span className="text-xs font-semibold text-slate-600">{b.count}</span>
            <div
              className="w-full bg-blue-500 rounded-t transition-all"
              style={{ height: `${Math.round((b.count / maxCount) * 100)}%`, minHeight: b.count > 0 ? '4px' : '0' }}
            />
            <div className="text-center">
              <div className="text-xs font-medium">{b.rating}</div>
              <div className="text-xs text-slate-400 leading-tight truncate w-16" title={b.label}>
                {b.label.replace(' Expectations', '')}
              </div>
            </div>
          </div>
        ))}
      </div>
      <p className="text-xs text-center text-slate-500">
        Total: {data.total} appraisals · 1–5 rating scale
      </p>
    </div>
  );
}

// ─── Appraisal Detail Dialog ──────────────────────────────────────────────────

function AppraisalDetailDialog({
  appraisalId,
  onClose,
}: {
  appraisalId: string;
  onClose: () => void;
}) {
  const { data: appraisal, isLoading } = useAppraisal(appraisalId);
  const submitSelf    = useSubmitSelfReview();
  const submitManager = useSubmitManagerReview();
  const { data: goals = [] } = useGoals(
    appraisal?.employee_id,
    appraisal?.cycle_id,
  );

  // Self-review form state
  const [selfForm, setSelfForm] = useState({
    self_achievements: '',
    self_improvements: '',
    self_strengths:    '',
    kpi_scores:        {} as Record<string, number>,
    competency_scores: {
      communication: 3, teamwork: 3, leadership: 3, problem_solving: 3, initiative: 3,
    } as Record<CompetencyKey, number>,
  });

  // Manager review form state
  const [mgrForm, setMgrForm] = useState({
    final_rating:          3,
    manager_feedback:      '',
    increment_recommended: false,
    increment_percentage:  null as number | null,
    promotion_recommended: false,
    kpi_scores:            {} as Record<string, number>,
    competency_scores: {
      communication: 3, teamwork: 3, leadership: 3, problem_solving: 3, initiative: 3,
    } as Record<CompetencyKey, number>,
    pip_recommended: false,
  });

  if (isLoading || !appraisal) return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent><div className="py-8 text-center text-slate-400">Loading…</div></DialogContent>
    </Dialog>
  );

  const canSelfReview    = ['self_review_pending', 'not_started'].includes(appraisal.status);
  const canManagerReview = ['self_review_submitted', 'manager_review_pending'].includes(appraisal.status);

  async function handleSelfSubmit(e: React.FormEvent) {
    e.preventDefault();
    await submitSelf.mutateAsync({ id: appraisalId, data: selfForm as any });
    onClose();
  }

  async function handleManagerSubmit(e: React.FormEvent) {
    e.preventDefault();
    await submitManager.mutateAsync({ id: appraisalId, data: mgrForm as any });
    onClose();
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            Appraisal — {appraisal.employee?.full_name ?? appraisal.employee_id}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Status bar */}
          <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
            <div className="text-sm text-slate-600">
              <span className="font-medium">Status: </span>
              <Badge className={APPRAISAL_STATUS_COLORS[appraisal.status as AppraisalStatus] ?? ''}>
                {APPRAISAL_STATUS_LABELS[appraisal.status as AppraisalStatus] ?? appraisal.status}
              </Badge>
            </div>
            {appraisal.final_rating !== null && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-500">Final:</span>
                {ratingStars(appraisal.final_rating)}
              </div>
            )}
          </div>

          {/* Ratings summary */}
          {(appraisal.self_rating || appraisal.manager_rating || appraisal.final_rating) && (
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: 'Self Rating',    value: appraisal.self_rating },
                { label: 'Manager Rating', value: appraisal.manager_rating },
                { label: 'Final Rating',   value: appraisal.final_rating },
              ].map(({ label, value }) => (
                <div key={label} className="p-3 border rounded-lg text-center">
                  <div className="text-xs text-slate-500 mb-1">{label}</div>
                  {ratingStars(value)}
                </div>
              ))}
            </div>
          )}

          {/* Goals table */}
          {goals.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold mb-2">Goals</h3>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Goal</TableHead>
                    <TableHead>Weight</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {goals.map((g) => (
                    <TableRow key={g.id}>
                      <TableCell className="font-medium text-sm">{g.title}</TableCell>
                      <TableCell className="text-sm">{g.weight}%</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs capitalize">
                          {g.status}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {/* Self Review Form */}
          {canSelfReview && (
            <form onSubmit={handleSelfSubmit} className="space-y-4 border rounded-lg p-4">
              <h3 className="font-semibold text-sm">Submit Self Review</h3>

              {/* Competency scores */}
              <div>
                <Label className="text-xs text-slate-500 mb-2 block">Competency Scores (1–5)</Label>
                <div className="grid grid-cols-2 gap-2">
                  {COMPETENCIES.map((key) => (
                    <div key={key} className="flex items-center gap-2">
                      <Label className="w-32 text-xs capitalize">{key.replace('_', ' ')}</Label>
                      <Input
                        type="number"
                        min={1}
                        max={5}
                        step={0.5}
                        className="w-20"
                        value={selfForm.competency_scores[key]}
                        onChange={(e) =>
                          setSelfForm((p) => ({
                            ...p,
                            competency_scores: { ...p.competency_scores, [key]: Number(e.target.value) },
                          }))
                        }
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* KPI scores per goal */}
              {goals.length > 0 && (
                <div>
                  <Label className="text-xs text-slate-500 mb-2 block">KPI Scores (1–5)</Label>
                  <div className="space-y-2">
                    {goals.map((g) => (
                      <div key={g.id} className="flex items-center gap-2">
                        <span className="flex-1 text-xs truncate">{g.title}</span>
                        <Input
                          type="number"
                          min={1}
                          max={5}
                          step={0.5}
                          className="w-20"
                          value={selfForm.kpi_scores[g.id] ?? 3}
                          onChange={(e) =>
                            setSelfForm((p) => ({
                              ...p,
                              kpi_scores: { ...p.kpi_scores, [g.id]: Number(e.target.value) },
                            }))
                          }
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="space-y-1">
                <Label>Key Achievements *</Label>
                <Textarea
                  required
                  minLength={20}
                  rows={3}
                  placeholder="Describe your achievements this period…"
                  value={selfForm.self_achievements}
                  onChange={(e) => setSelfForm((p) => ({ ...p, self_achievements: e.target.value }))}
                />
              </div>
              <div className="space-y-1">
                <Label>Strengths *</Label>
                <Textarea
                  required
                  minLength={20}
                  rows={2}
                  placeholder="What are your key strengths?"
                  value={selfForm.self_strengths}
                  onChange={(e) => setSelfForm((p) => ({ ...p, self_strengths: e.target.value }))}
                />
              </div>
              <div className="space-y-1">
                <Label>Areas for Improvement *</Label>
                <Textarea
                  required
                  minLength={20}
                  rows={2}
                  placeholder="What would you like to improve?"
                  value={selfForm.self_improvements}
                  onChange={(e) => setSelfForm((p) => ({ ...p, self_improvements: e.target.value }))}
                />
              </div>
              <Button type="submit" disabled={submitSelf.isPending} className="w-full">
                {submitSelf.isPending ? 'Submitting…' : 'Submit Self Review'}
              </Button>
            </form>
          )}

          {/* Manager Review Form */}
          {canManagerReview && (
            <form onSubmit={handleManagerSubmit} className="space-y-4 border rounded-lg p-4 bg-blue-50/30">
              <h3 className="font-semibold text-sm">Submit Manager Review</h3>

              {/* Competency scores */}
              <div>
                <Label className="text-xs text-slate-500 mb-2 block">Competency Scores (1–5)</Label>
                <div className="grid grid-cols-2 gap-2">
                  {COMPETENCIES.map((key) => (
                    <div key={key} className="flex items-center gap-2">
                      <Label className="w-32 text-xs capitalize">{key.replace('_', ' ')}</Label>
                      <Input
                        type="number"
                        min={1}
                        max={5}
                        step={0.5}
                        className="w-20 bg-white"
                        value={mgrForm.competency_scores[key as CompetencyKey]}
                        onChange={(e) =>
                          setMgrForm((p) => ({
                            ...p,
                            competency_scores: { ...p.competency_scores, [key]: Number(e.target.value) },
                          }))
                        }
                      />
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-1">
                <Label>Final Rating (1–5) *</Label>
                <Input
                  type="number"
                  min={1}
                  max={5}
                  step={0.5}
                  required
                  className="bg-white"
                  value={mgrForm.final_rating}
                  onChange={(e) => setMgrForm((p) => ({ ...p, final_rating: Number(e.target.value) }))}
                />
              </div>
              <div className="space-y-1">
                <Label>Manager Feedback *</Label>
                <Textarea
                  required
                  minLength={50}
                  rows={3}
                  className="bg-white"
                  placeholder="Detailed performance feedback (min 50 chars)…"
                  value={mgrForm.manager_feedback}
                  onChange={(e) => setMgrForm((p) => ({ ...p, manager_feedback: e.target.value }))}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={mgrForm.increment_recommended}
                    onChange={(e) => setMgrForm((p) => ({ ...p, increment_recommended: e.target.checked }))}
                  />
                  <span className="text-sm">Increment Recommended</span>
                </label>
                {mgrForm.increment_recommended && (
                  <div className="space-y-1">
                    <Label className="text-xs">Increment %</Label>
                    <Input
                      type="number"
                      min={0}
                      max={100}
                      step={0.5}
                      className="bg-white"
                      value={mgrForm.increment_percentage ?? ''}
                      onChange={(e) => setMgrForm((p) => ({ ...p, increment_percentage: Number(e.target.value) }))}
                    />
                  </div>
                )}
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={mgrForm.promotion_recommended}
                    onChange={(e) => setMgrForm((p) => ({ ...p, promotion_recommended: e.target.checked }))}
                  />
                  <span className="text-sm">Promotion Recommended</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={mgrForm.pip_recommended}
                    onChange={(e) => setMgrForm((p) => ({ ...p, pip_recommended: e.target.checked }))}
                  />
                  <span className="text-sm text-red-600">PIP Required</span>
                </label>
              </div>
              <Button type="submit" disabled={submitManager.isPending} className="w-full">
                {submitManager.isPending ? 'Submitting…' : 'Submit Manager Review'}
              </Button>
            </form>
          )}

          {/* Existing review summary (read-only) */}
          {appraisal.manager_feedback && !canManagerReview && (
            <div className="p-3 bg-slate-50 rounded-lg space-y-2">
              <h3 className="text-sm font-semibold">Manager Feedback</h3>
              <p className="text-sm text-slate-600">{appraisal.manager_feedback}</p>
              {appraisal.increment_recommended && (
                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                  Increment: {appraisal.increment_percentage ?? '—'}%
                </Badge>
              )}
              {appraisal.promotion_recommended && (
                <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200 ml-2">
                  Promotion Recommended
                </Badge>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── Cycle Detail Panel ───────────────────────────────────────────────────────

function CycleDetailPanel({
  cycle,
  onBack,
}: {
  cycle: AppraisalCycle;
  onBack: () => void;
}) {
  const [selectedAppraisalId, setSelectedAppraisalId] = useState<string | null>(null);
  const { data: appraisals, isLoading } = useAppraisals({ cycle_id: cycle.id });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={onBack}>← Back</Button>
        <div>
          <h2 className="text-lg font-semibold">{cycle.name}</h2>
          <p className="text-sm text-slate-500">{cycle.start_date} → {cycle.end_date}</p>
        </div>
        <Badge variant="outline" className={`ml-auto ${CYCLE_STATUS_COLORS[cycle.status as CycleStatus]}`}>
          {cycle.status.replace(/_/g, ' ')}
        </Badge>
      </div>

      <Tabs defaultValue="appraisals">
        <TabsList>
          <TabsTrigger value="appraisals">Appraisals</TabsTrigger>
          <TabsTrigger value="bell-curve">Bell Curve</TabsTrigger>
        </TabsList>

        <TabsContent value="appraisals" className="pt-3">
          {isLoading ? (
            <div className="py-8 text-center text-slate-400">Loading…</div>
          ) : !appraisals?.results.length ? (
            <div className="py-8 text-center text-slate-400">
              No appraisals yet. Launch the cycle to create records.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Employee</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Self</TableHead>
                  <TableHead>Manager</TableHead>
                  <TableHead>Final</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {appraisals.results.map((a) => (
                  <TableRow key={a.id} className="cursor-pointer hover:bg-slate-50">
                    <TableCell>
                      <div className="font-medium text-sm">
                        {a.employee?.full_name ?? a.employee_id}
                      </div>
                      <div className="text-xs text-slate-400">
                        {a.employee?.department}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={`text-xs ${APPRAISAL_STATUS_COLORS[a.status as AppraisalStatus] ?? ''}`}>
                        {APPRAISAL_STATUS_LABELS[a.status as AppraisalStatus] ?? a.status}
                      </Badge>
                    </TableCell>
                    <TableCell>{ratingStars(a.self_rating)}</TableCell>
                    <TableCell>{ratingStars(a.manager_rating)}</TableCell>
                    <TableCell>{ratingStars(a.final_rating)}</TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setSelectedAppraisalId(a.id)}
                      >
                        <Eye className="h-3.5 w-3.5" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </TabsContent>

        <TabsContent value="bell-curve" className="pt-3">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Rating Distribution</CardTitle>
              <CardDescription>Bell curve across all completed appraisals</CardDescription>
            </CardHeader>
            <CardContent>
              <BellCurveChart cycleId={cycle.id} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {selectedAppraisalId && (
        <AppraisalDetailDialog
          appraisalId={selectedAppraisalId}
          onClose={() => setSelectedAppraisalId(null)}
        />
      )}
    </div>
  );
}

// ─── My Appraisal Card ────────────────────────────────────────────────────────

function MyAppraisalCard({ onOpen }: { onOpen: (id: string) => void }) {
  const { data: appraisal, isLoading } = useMyAppraisal();

  if (isLoading) return null;
  if (!appraisal) return (
    <Card className="border-dashed">
      <CardContent className="py-6 text-center text-slate-400 text-sm">
        No active appraisal cycle at this time.
      </CardContent>
    </Card>
  );

  return (
    <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">My Current Appraisal</CardTitle>
          <Badge className={APPRAISAL_STATUS_COLORS[appraisal.status as AppraisalStatus] ?? ''}>
            {APPRAISAL_STATUS_LABELS[appraisal.status as AppraisalStatus] ?? appraisal.status}
          </Badge>
        </div>
        <CardDescription>{appraisal.cycle?.name}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-3 gap-2 text-center">
          {[
            { label: 'Self',    value: appraisal.self_rating },
            { label: 'Manager', value: appraisal.manager_rating },
            { label: 'Final',   value: appraisal.final_rating },
          ].map(({ label, value }) => (
            <div key={label} className="p-2 bg-white rounded-lg">
              <div className="text-xs text-slate-500 mb-1">{label}</div>
              {value !== null
                ? <span className="text-lg font-bold text-blue-700">{value?.toFixed(1)}</span>
                : <span className="text-slate-300 text-sm">—</span>
              }
            </div>
          ))}
        </div>
        <Button size="sm" className="w-full" onClick={() => onOpen(appraisal.id)}>
          {['self_review_pending', 'not_started'].includes(appraisal.status)
            ? 'Submit Self Review'
            : 'View Appraisal'
          }
          <ChevronRight className="h-3.5 w-3.5 ml-1" />
        </Button>
      </CardContent>
    </Card>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function PerformancePage() {
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedCycle, setSelectedCycle]       = useState<AppraisalCycle | null>(null);
  const [openAppraisalId, setOpenAppraisalId]   = useState<string | null>(null);

  const { data: cyclesData, isLoading, refetch } = useCycles();
  const cycles = cyclesData?.results ?? [];

  const activeCycle    = cycles.find((c) => ['active', 'self_review', 'manager_review'].includes(c.status));
  const upcomingCycles = cycles.filter((c) => c.status === 'upcoming');
  const pastCycles     = cycles.filter((c) => ['completed', 'archived'].includes(c.status));

  if (selectedCycle) {
    return (
      <div className="p-6">
        <CycleDetailPanel
          cycle={selectedCycle}
          onBack={() => setSelectedCycle(null)}
        />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <BarChart3 className="h-6 w-6 text-blue-600" />
            Performance Management
          </h1>
          <p className="text-slate-500 text-sm mt-0.5">
            Appraisal cycles, goals, reviews &amp; bell curves
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
          <Button size="sm" onClick={() => setShowCreateDialog(true)}>
            <Plus className="h-4 w-4 mr-1" />
            New Cycle
          </Button>
        </div>
      </div>

      {/* My current appraisal */}
      <MyAppraisalCard onOpen={setOpenAppraisalId} />

      {/* Active cycle */}
      {activeCycle && (
        <div>
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
            Active Cycle
          </h2>
          <CycleCard cycle={activeCycle} onSelect={setSelectedCycle} />
        </div>
      )}

      {/* Upcoming */}
      {upcomingCycles.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
            Upcoming
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {upcomingCycles.map((c) => (
              <CycleCard key={c.id} cycle={c} onSelect={setSelectedCycle} />
            ))}
          </div>
        </div>
      )}

      {/* Past cycles */}
      {pastCycles.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
            Past Cycles
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {pastCycles.map((c) => (
              <CycleCard key={c.id} cycle={c} onSelect={setSelectedCycle} />
            ))}
          </div>
        </div>
      )}

      {!isLoading && cycles.length === 0 && (
        <div className="text-center py-20 text-slate-400">
          <BarChart3 className="h-12 w-12 mx-auto mb-3 opacity-20" />
          <p className="font-medium">No appraisal cycles yet</p>
          <p className="text-sm">Create one to get started</p>
        </div>
      )}

      {/* Dialogs */}
      <CreateCycleDialog
        open={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
      />
      {openAppraisalId && (
        <AppraisalDetailDialog
          appraisalId={openAppraisalId}
          onClose={() => setOpenAppraisalId(null)}
        />
      )}
    </div>
  );
}
