'use client';

import { useState } from 'react';
import {
  GraduationCap, Plus, Search, Filter, Users, Clock, Award,
  BookOpen, Calendar, RefreshCw, Eye, Trash2, MoreHorizontal,
  CheckCircle, AlertCircle, Play, X,
} from 'lucide-react';

import { Button }    from '@/components/ui/button';
import { Badge }     from '@/components/ui/badge';
import { Input }     from '@/components/ui/input';
import { Label }     from '@/components/ui/label';
import { Textarea }  from '@/components/ui/textarea';
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
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

import {
  useTrainingStats,
  usePrograms,
  useProgram,
  useCreateProgram,
  useUpdateProgram,
  useDeleteProgram,
  useChangeStatus,
  useEnrollments,
  useEnrollEmployees,
  useUpdateEnrollment,
  useMyEnrollments,
} from '@/hooks/useTraining';

import type {
  TrainingProgram,
  TrainingProgramCreate,
  TrainingStatus,
  EnrollmentStatus,
  TrainingFilterParams,
} from '@/types/training';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const STATUS_COLORS: Record<TrainingStatus, string> = {
  planned:           'bg-slate-100 text-slate-600 border-slate-200',
  registration_open: 'bg-blue-50  text-blue-700  border-blue-200',
  ongoing:           'bg-green-50 text-green-700  border-green-200',
  completed:         'bg-purple-50 text-purple-700 border-purple-200',
  cancelled:         'bg-red-50  text-red-600    border-red-200',
};

const ENROLLMENT_STATUS_COLORS: Record<EnrollmentStatus, string> = {
  enrolled:    'bg-blue-50   text-blue-700',
  in_progress: 'bg-yellow-50 text-yellow-700',
  completed:   'bg-green-50  text-green-700',
  failed:      'bg-red-50    text-red-600',
  absent:      'bg-orange-50 text-orange-700',
  dropped:     'bg-slate-100 text-slate-500',
};

const STATUS_TRANSITIONS: Record<TrainingStatus, TrainingStatus[]> = {
  planned:           ['registration_open', 'cancelled'],
  registration_open: ['ongoing', 'cancelled'],
  ongoing:           ['completed', 'cancelled'],
  completed:         [],
  cancelled:         [],
};

const MODE_LABELS: Record<string, string> = {
  online:    'Online',
  in_person: 'In Person',
  hybrid:    'Hybrid',
  self_paced: 'Self-Paced',
};

// ─── Stats Cards ─────────────────────────────────────────────────────────────

function StatsCards() {
  const { data: stats } = useTrainingStats();

  const cards = [
    { label: 'Total Programs',  value: stats?.total_programs    ?? '—', icon: BookOpen,    color: 'text-blue-600'   },
    { label: 'Ongoing',         value: stats?.active_programs   ?? '—', icon: Play,        color: 'text-green-600'  },
    { label: 'Total Enrollments', value: stats?.total_enrollments ?? '—', icon: Users,    color: 'text-purple-600' },
    { label: 'Completion Rate', value: stats ? `${stats.completion_rate}%` : '—', icon: Award, color: 'text-amber-600' },
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map(({ label, value, icon: Icon, color }) => (
        <Card key={label}>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-500">{label}</p>
                <p className="text-2xl font-bold mt-0.5">{value}</p>
              </div>
              <Icon className={`h-8 w-8 ${color} opacity-80`} />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ─── Create / Edit Program Dialog ────────────────────────────────────────────

function ProgramFormDialog({
  open,
  initial,
  onClose,
}: {
  open:     boolean;
  initial?: TrainingProgram;
  onClose:  () => void;
}) {
  const createProgram = useCreateProgram();
  const updateProgram = useUpdateProgram();
  const isEdit = !!initial;

  const [form, setForm] = useState<TrainingProgramCreate>({
    title:          initial?.title          ?? '',
    description:    initial?.description    ?? '',
    category:       initial?.category       ?? '',
    mode:           initial?.mode           ?? 'in_person',
    trainer:        initial?.trainer        ?? '',
    venue:          initial?.venue          ?? '',
    start_date:     initial?.start_date     ?? null,
    end_date:       initial?.end_date       ?? null,
    duration_hours: initial?.duration_hours ?? null,
    max_participants: initial?.max_participants ?? null,
    cost_per_participant: initial?.cost_per_participant ?? null,
    is_mandatory:   initial?.is_mandatory   ?? false,
    issues_certificate: initial?.issues_certificate ?? false,
    certificate_validity_months: initial?.certificate_validity_months ?? null,
    material_url:   initial?.material_url   ?? null,
    external_url:   initial?.external_url   ?? null,
    skills_covered: initial?.skills_covered ?? [],
  });

  const [skillInput, setSkillInput] = useState('');

  function set(k: keyof TrainingProgramCreate, v: unknown) {
    setForm((p) => ({ ...p, [k]: v }));
  }

  function addSkill() {
    const s = skillInput.trim();
    if (s && !form.skills_covered?.includes(s)) {
      setForm((p) => ({ ...p, skills_covered: [...(p.skills_covered ?? []), s] }));
    }
    setSkillInput('');
  }

  function removeSkill(s: string) {
    setForm((p) => ({ ...p, skills_covered: p.skills_covered?.filter((x) => x !== s) }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (isEdit && initial) {
      await updateProgram.mutateAsync({ id: initial.id, data: form });
    } else {
      await createProgram.mutateAsync(form);
    }
    onClose();
  }

  const isPending = createProgram.isPending || updateProgram.isPending;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit' : 'New'} Training Program</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2 space-y-1">
              <Label>Title *</Label>
              <Input
                required
                value={form.title}
                onChange={(e) => set('title', e.target.value)}
                placeholder="e.g. Python for Beginners"
              />
            </div>
            <div className="col-span-2 space-y-1">
              <Label>Description</Label>
              <Textarea
                rows={2}
                value={form.description ?? ''}
                onChange={(e) => set('description', e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label>Category</Label>
              <Input
                value={form.category ?? ''}
                onChange={(e) => set('category', e.target.value)}
                placeholder="e.g. Technical, Compliance"
              />
            </div>
            <div className="space-y-1">
              <Label>Mode</Label>
              <Select value={form.mode} onValueChange={(v) => set('mode', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(MODE_LABELS).map(([v, l]) => (
                    <SelectItem key={v} value={v}>{l}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>Start Date</Label>
              <Input
                type="date"
                value={form.start_date ?? ''}
                onChange={(e) => set('start_date', e.target.value || null)}
              />
            </div>
            <div className="space-y-1">
              <Label>End Date</Label>
              <Input
                type="date"
                value={form.end_date ?? ''}
                onChange={(e) => set('end_date', e.target.value || null)}
              />
            </div>
            <div className="space-y-1">
              <Label>Trainer Name</Label>
              <Input
                value={form.trainer ?? ''}
                onChange={(e) => set('trainer', e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label>Venue / Location</Label>
              <Input
                value={form.venue ?? ''}
                onChange={(e) => set('venue', e.target.value)}
                placeholder={form.mode === 'online' ? 'URL or virtual room' : 'Room / Building'}
              />
            </div>
            <div className="space-y-1">
              <Label>Duration (hours)</Label>
              <Input
                type="number"
                min={0.5}
                step={0.5}
                value={form.duration_hours ?? ''}
                onChange={(e) => set('duration_hours', e.target.value ? Number(e.target.value) : null)}
              />
            </div>
            <div className="space-y-1">
              <Label>Max Participants</Label>
              <Input
                type="number"
                min={1}
                value={form.max_participants ?? ''}
                onChange={(e) => set('max_participants', e.target.value ? Number(e.target.value) : null)}
              />
            </div>
            <div className="space-y-1">
              <Label>Cost per Participant (PKR)</Label>
              <Input
                type="number"
                min={0}
                value={form.cost_per_participant ?? ''}
                onChange={(e) => set('cost_per_participant', e.target.value ? Number(e.target.value) : null)}
              />
            </div>
            <div className="space-y-1">
              <Label>Material / Syllabus URL</Label>
              <Input
                value={form.material_url ?? ''}
                onChange={(e) => set('material_url', e.target.value || null)}
              />
            </div>

            {/* Skills covered */}
            <div className="col-span-2 space-y-2">
              <Label>Skills Covered</Label>
              <div className="flex gap-2">
                <Input
                  value={skillInput}
                  onChange={(e) => setSkillInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addSkill(); } }}
                  placeholder="Type a skill and press Enter"
                />
                <Button type="button" variant="outline" size="sm" onClick={addSkill}>Add</Button>
              </div>
              {(form.skills_covered?.length ?? 0) > 0 && (
                <div className="flex flex-wrap gap-1">
                  {form.skills_covered!.map((s) => (
                    <Badge key={s} variant="secondary" className="gap-1 cursor-pointer" onClick={() => removeSkill(s)}>
                      {s} <X className="h-3 w-3" />
                    </Badge>
                  ))}
                </div>
              )}
            </div>

            {/* Flags */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.is_mandatory ?? false}
                onChange={(e) => set('is_mandatory', e.target.checked)}
              />
              <span className="text-sm font-medium">Mandatory Training</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.issues_certificate ?? false}
                onChange={(e) => set('issues_certificate', e.target.checked)}
              />
              <span className="text-sm font-medium">Issues Certificate</span>
            </label>
            {form.issues_certificate && (
              <div className="space-y-1">
                <Label>Certificate Validity (months)</Label>
                <Input
                  type="number"
                  min={1}
                  value={form.certificate_validity_months ?? ''}
                  onChange={(e) => set('certificate_validity_months', e.target.value ? Number(e.target.value) : null)}
                />
              </div>
            )}
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? 'Saving…' : isEdit ? 'Save Changes' : 'Create Program'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Program Detail Dialog ────────────────────────────────────────────────────

function ProgramDetailDialog({
  programId,
  onClose,
}: {
  programId: string;
  onClose:   () => void;
}) {
  const { data: program, isLoading } = useProgram(programId);
  const { data: enrollments = []   } = useEnrollments(programId);
  const updateEnrollment = useUpdateEnrollment();
  const enrollEmployees  = useEnrollEmployees();
  const changeStatus     = useChangeStatus();
  const [enrollIdInput, setEnrollIdInput] = useState('');

  if (isLoading || !program) return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent><div className="py-8 text-center text-slate-400">Loading…</div></DialogContent>
    </Dialog>
  );

  const nextStatuses = STATUS_TRANSITIONS[program.status as TrainingStatus] ?? [];

  async function handleEnroll() {
    const ids = enrollIdInput.split(/[\s,]+/).filter(Boolean);
    if (!ids.length) return;
    await enrollEmployees.mutateAsync({ programId, data: { employee_ids: ids } });
    setEnrollIdInput('');
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GraduationCap className="h-5 w-5 text-blue-600" />
            {program.title}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Info grid */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-slate-500">Status: </span>
              <Badge variant="outline" className={STATUS_COLORS[program.status as TrainingStatus]}>
                {program.status.replace(/_/g, ' ')}
              </Badge>
            </div>
            <div><span className="text-slate-500">Mode: </span>{MODE_LABELS[program.mode] ?? program.mode}</div>
            {program.start_date && <div><span className="text-slate-500">Start: </span>{program.start_date}</div>}
            {program.end_date   && <div><span className="text-slate-500">End: </span>{program.end_date}</div>}
            {program.trainer    && <div><span className="text-slate-500">Trainer: </span>{program.trainer}</div>}
            {program.venue      && <div><span className="text-slate-500">Venue: </span>{program.venue}</div>}
            <div>
              <span className="text-slate-500">Enrolled: </span>
              {program.enrolled_count}
              {program.max_participants ? ` / ${program.max_participants}` : ''}
            </div>
            {program.duration_hours && (
              <div><span className="text-slate-500">Duration: </span>{program.duration_hours}h</div>
            )}
          </div>

          {program.description && (
            <p className="text-sm text-slate-600">{program.description}</p>
          )}

          {program.skills_covered && program.skills_covered.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {program.skills_covered.map((s) => (
                <Badge key={s} variant="secondary" className="text-xs">{s}</Badge>
              ))}
            </div>
          )}

          {/* Status transitions */}
          {nextStatuses.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Move to:</span>
              {nextStatuses.map((s) => (
                <Button
                  key={s}
                  size="sm"
                  variant="outline"
                  onClick={() => changeStatus.mutate({ id: programId, newStatus: s })}
                  disabled={changeStatus.isPending}
                >
                  {s.replace(/_/g, ' ')}
                </Button>
              ))}
            </div>
          )}

          {/* Enroll */}
          {['registration_open', 'planned', 'ongoing'].includes(program.status) && (
            <div className="border rounded-lg p-3 space-y-2">
              <h3 className="text-sm font-semibold">Enroll Employees</h3>
              <div className="flex gap-2">
                <Input
                  placeholder="Employee IDs (comma or space separated)"
                  value={enrollIdInput}
                  onChange={(e) => setEnrollIdInput(e.target.value)}
                  className="flex-1"
                />
                <Button size="sm" onClick={handleEnroll} disabled={enrollEmployees.isPending}>
                  Enroll
                </Button>
              </div>
            </div>
          )}

          {/* Enrollments table */}
          {enrollments.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold mb-2">Participants ({enrollments.length})</h3>
              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Employee</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Score</TableHead>
                      <TableHead>Attendance</TableHead>
                      <TableHead>Certificate</TableHead>
                      <TableHead />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {enrollments.map((e) => (
                      <TableRow key={e.id}>
                        <TableCell className="text-sm font-medium">
                          {e.employee?.full_name ?? e.employee_id}
                        </TableCell>
                        <TableCell>
                          <Select
                            value={e.status}
                            onValueChange={(v) =>
                              updateEnrollment.mutate({ id: e.id, data: { status: v as EnrollmentStatus } })
                            }
                          >
                            <SelectTrigger className="h-7 text-xs w-36">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {(['enrolled', 'in_progress', 'completed', 'failed', 'absent', 'dropped'] as EnrollmentStatus[]).map((s) => (
                                <SelectItem key={s} value={s}>{s.replace(/_/g, ' ')}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </TableCell>
                        <TableCell className="text-sm">
                          {e.score != null ? `${e.score}%` : '—'}
                        </TableCell>
                        <TableCell className="text-sm">
                          {e.attendance_percentage != null ? `${e.attendance_percentage}%` : '—'}
                        </TableCell>
                        <TableCell>
                          {e.certificate_issued_at ? (
                            <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 text-xs">
                              <Award className="h-3 w-3 mr-1" />
                              Issued
                            </Badge>
                          ) : (
                            <span className="text-slate-300 text-xs">—</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {/* Quick score update */}
                          {e.status === 'completed' && e.score == null && (
                            <Button
                              size="sm"
                              variant="ghost"
                              className="text-xs h-7"
                              onClick={() => {
                                const score = prompt('Enter score (0-100):');
                                if (score) {
                                  updateEnrollment.mutate({ id: e.id, data: { score: Number(score) } });
                                }
                              }}
                            >
                              Add Score
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── Program Card ─────────────────────────────────────────────────────────────

function ProgramCard({
  program,
  onView,
  onEdit,
}: {
  program: TrainingProgram;
  onView:  () => void;
  onEdit:  () => void;
}) {
  const deleteProgram = useDeleteProgram();
  const enrolledPct   = program.max_participants
    ? Math.round((program.enrolled_count / program.max_participants) * 100)
    : null;

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-base font-semibold truncate">{program.title}</CardTitle>
            <CardDescription className="flex items-center gap-2 flex-wrap mt-0.5">
              {program.category && <span>{program.category}</span>}
              {program.category && program.start_date && <span>·</span>}
              {program.start_date && (
                <span className="flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  {program.start_date}
                </span>
              )}
            </CardDescription>
          </div>
          <div className="flex items-center gap-1 flex-shrink-0">
            <Badge variant="outline" className={STATUS_COLORS[program.status as TrainingStatus] ?? ''}>
              {program.status.replace(/_/g, ' ')}
            </Badge>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-7 w-7 p-0">
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={onView}>
                  <Eye className="h-4 w-4 mr-2" />View & Enroll
                </DropdownMenuItem>
                <DropdownMenuItem onClick={onEdit}>
                  Edit Details
                </DropdownMenuItem>
                {['planned', 'cancelled'].includes(program.status) && (
                  <DropdownMenuItem
                    className="text-red-600"
                    onClick={() => {
                      if (confirm('Delete this program?')) {
                        deleteProgram.mutate(program.id);
                      }
                    }}
                  >
                    <Trash2 className="h-4 w-4 mr-2" />Delete
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span className="flex items-center gap-1">
            <Users className="h-3.5 w-3.5" />
            {program.enrolled_count}
            {program.max_participants ? ` / ${program.max_participants}` : ''}
          </span>
          {program.duration_hours && (
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              {program.duration_hours}h
            </span>
          )}
          <span className="capitalize">{MODE_LABELS[program.mode] ?? program.mode}</span>
          {program.is_mandatory && (
            <Badge variant="outline" className="text-xs bg-red-50 text-red-600 border-red-200">
              Mandatory
            </Badge>
          )}
          {program.issues_certificate && (
            <Badge variant="outline" className="text-xs bg-amber-50 text-amber-700 border-amber-200">
              <Award className="h-3 w-3 mr-1" />Cert
            </Badge>
          )}
        </div>

        {enrolledPct !== null && (
          <div>
            <div className="flex justify-between text-xs text-slate-400 mb-1">
              <span>Capacity</span>
              <span>{enrolledPct}%</span>
            </div>
            <Progress value={enrolledPct} className="h-1.5" />
          </div>
        )}

        {program.skills_covered && program.skills_covered.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {program.skills_covered.slice(0, 3).map((s) => (
              <Badge key={s} variant="secondary" className="text-xs">{s}</Badge>
            ))}
            {program.skills_covered.length > 3 && (
              <Badge variant="secondary" className="text-xs">+{program.skills_covered.length - 3}</Badge>
            )}
          </div>
        )}

        <Button size="sm" variant="outline" className="w-full mt-1" onClick={onView}>
          <Eye className="h-3.5 w-3.5 mr-1" />
          View Details
        </Button>
      </CardContent>
    </Card>
  );
}

// ─── My Trainings Tab ─────────────────────────────────────────────────────────

function MyTrainingsTab() {
  const { data: enrollments = [], isLoading } = useMyEnrollments();

  if (isLoading) return <div className="py-8 text-center text-slate-400">Loading…</div>;
  if (!enrollments.length) return (
    <div className="py-8 text-center text-slate-400">
      <GraduationCap className="h-10 w-10 mx-auto mb-2 opacity-20" />
      <p>You have no training enrollments.</p>
    </div>
  );

  return (
    <div className="space-y-3">
      {enrollments.map((e) => (
        <Card key={e.id} className="hover:shadow-sm transition-shadow">
          <CardContent className="py-3 px-4">
            <div className="flex items-center justify-between gap-3">
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm truncate">
                  {(e as any).program?.title ?? `Program ${e.program_id}`}
                </p>
                <div className="flex items-center gap-2 mt-0.5 text-xs text-slate-400">
                  {(e as any).program?.start_date && (
                    <span>{(e as any).program.start_date}</span>
                  )}
                  {e.score != null && <span>Score: {e.score}%</span>}
                  {e.attendance_percentage != null && <span>Attendance: {e.attendance_percentage}%</span>}
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <Badge className={`text-xs ${ENROLLMENT_STATUS_COLORS[e.status as EnrollmentStatus] ?? ''}`}>
                  {e.status.replace(/_/g, ' ')}
                </Badge>
                {e.certificate_issued_at && (
                  <Badge variant="outline" className="text-xs bg-amber-50 text-amber-700 border-amber-200">
                    <Award className="h-3 w-3 mr-1" />Certified
                  </Badge>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function TrainingPage() {
  const [showCreate, setShowCreate]           = useState(false);
  const [editProgram, setEditProgram]         = useState<TrainingProgram | null>(null);
  const [viewProgramId, setViewProgramId]     = useState<string | null>(null);
  const [search, setSearch]                   = useState('');
  const [statusFilter, setStatusFilter]       = useState<string>('');
  const [mandatoryFilter, setMandatoryFilter] = useState<string>('');

  const filters: Partial<TrainingFilterParams> = {
    search:       search || undefined,
    status:       statusFilter as any || undefined,
    is_mandatory: mandatoryFilter === 'yes' ? true : mandatoryFilter === 'no' ? false : undefined,
  };

  const { data: programsData, isLoading, refetch } = usePrograms(filters);
  const programs = programsData?.results ?? [];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <GraduationCap className="h-6 w-6 text-blue-600" />
            Training Management
          </h1>
          <p className="text-slate-500 text-sm mt-0.5">
            Programs, enrollments, certifications &amp; compliance
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="h-4 w-4 mr-1" />
            New Program
          </Button>
        </div>
      </div>

      {/* Stats */}
      <StatsCards />

      {/* Tabs */}
      <Tabs defaultValue="programs">
        <TabsList>
          <TabsTrigger value="programs">All Programs</TabsTrigger>
          <TabsTrigger value="my">My Training</TabsTrigger>
        </TabsList>

        <TabsContent value="programs" className="space-y-4 pt-2">
          {/* Filters */}
          <div className="flex flex-wrap gap-2">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
              <Input
                className="pl-8"
                placeholder="Search programs…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <Select value={statusFilter || 'all'} onValueChange={(v) => setStatusFilter(v === 'all' ? '' : v)}>
              <SelectTrigger className="w-44">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="planned">Planned</SelectItem>
                <SelectItem value="registration_open">Registration Open</SelectItem>
                <SelectItem value="ongoing">Ongoing</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>
            <Select value={mandatoryFilter || 'all'} onValueChange={(v) => setMandatoryFilter(v === 'all' ? '' : v)}>
              <SelectTrigger className="w-36">
                <SelectValue placeholder="All Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="yes">Mandatory Only</SelectItem>
                <SelectItem value="no">Optional Only</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Grid */}
          {isLoading ? (
            <div className="py-12 text-center text-slate-400">Loading…</div>
          ) : programs.length === 0 ? (
            <div className="py-16 text-center text-slate-400">
              <GraduationCap className="h-12 w-12 mx-auto mb-3 opacity-20" />
              <p className="font-medium">No programs found</p>
              <p className="text-sm">Create one to get started</p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {programs.map((p) => (
                <ProgramCard
                  key={p.id}
                  program={p}
                  onView={() => setViewProgramId(p.id)}
                  onEdit={() => setEditProgram(p)}
                />
              ))}
            </div>
          )}

          {/* Count */}
          {programsData && (
            <p className="text-xs text-slate-400 text-center">
              Showing {programs.length} of {programsData.count} programs
            </p>
          )}
        </TabsContent>

        <TabsContent value="my" className="pt-2">
          <MyTrainingsTab />
        </TabsContent>
      </Tabs>

      {/* Dialogs */}
      <ProgramFormDialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
      />
      {editProgram && (
        <ProgramFormDialog
          open
          initial={editProgram}
          onClose={() => setEditProgram(null)}
        />
      )}
      {viewProgramId && (
        <ProgramDetailDialog
          programId={viewProgramId}
          onClose={() => setViewProgramId(null)}
        />
      )}
    </div>
  );
}
