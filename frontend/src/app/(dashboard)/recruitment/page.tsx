'use client';

import { useState } from 'react';
import {
  Plus, Search, Filter, Briefcase, Users, Calendar,
  Building2, Clock, ChevronRight, Download, Eye,
} from 'lucide-react';

import { Button }   from '@/components/ui/button';
import { Input }    from '@/components/ui/input';
import { Badge }    from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Sheet,
  SheetContent,
} from '@/components/ui/sheet';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

import { JobPostingForm }          from '@/components/recruitment/JobPostingForm';
import { KanbanBoard }             from '@/components/recruitment/KanbanBoard';
import { ApplicationDetailPanel }  from '@/components/recruitment/ApplicationDetailPanel';
import { ScheduleInterviewDialog } from '@/components/recruitment/ScheduleInterviewDialog';
import { OfferLetterDialog }       from '@/components/recruitment/OfferLetterDialog';
import { AIScoreCard }             from '@/components/recruitment/AIScoreCard';

import {
  useJobPostings,
  useJobPosting,
  useCreateJob,
  useUpdateJob,
  usePublishJob,
  useCloseJob,
  useApplications,
  useApplicationInterviews,
} from '@/hooks/useRecruitment';

import type {
  JobStatus,
  ApplicationStatus,
  JobPostingCreate,
  JobPostingResponse,
} from '@/types/recruitment';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const JOB_STATUS_COLORS: Record<JobStatus, string> = {
  draft:   'bg-slate-100 text-slate-600 border-slate-200',
  open:    'bg-green-50 text-green-700 border-green-200',
  closed:  'bg-red-50 text-red-600 border-red-200',
  on_hold: 'bg-amber-50 text-amber-700 border-amber-200',
  filled:  'bg-blue-50 text-blue-700 border-blue-200',
};

const APP_STATUS_COLORS: Record<ApplicationStatus, string> = {
  applied:     'bg-slate-100 text-slate-700',
  screening:   'bg-blue-50 text-blue-700',
  shortlisted: 'bg-indigo-50 text-indigo-700',
  interview:   'bg-violet-50 text-violet-700',
  offered:     'bg-amber-50 text-amber-700',
  hired:       'bg-green-50 text-green-700',
  rejected:    'bg-red-50 text-red-600',
  withdrawn:   'bg-slate-100 text-slate-500',
};

function formatDate(iso: string | null) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-PK', { day: '2-digit', month: 'short', year: 'numeric' });
}

// ─── Summary cards ────────────────────────────────────────────────────────────

function SummaryCards({
  total, open: openCount, applications, interviews,
}: {
  total:        number;
  open:         number;
  applications: number;
  interviews:   number;
}) {
  const cards = [
    { label: 'Total Postings',    value: total,        icon: Briefcase, color: 'text-slate-600' },
    { label: 'Open Positions',    value: openCount,    icon: Building2, color: 'text-green-600' },
    { label: 'Total Applications',value: applications, icon: Users,     color: 'text-blue-600' },
    { label: 'Scheduled Interviews', value: interviews, icon: Calendar, color: 'text-violet-600' },
  ];
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((c) => (
        <div key={c.label} className="rounded-xl border bg-white p-4 flex items-center gap-3">
          <div className={`rounded-lg bg-slate-50 p-2.5 ${c.color}`}>
            <c.icon className="h-5 w-5" />
          </div>
          <div>
            <p className="text-2xl font-bold text-slate-900">{c.value}</p>
            <p className="text-xs text-slate-500">{c.label}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Job Postings tab ─────────────────────────────────────────────────────────

function JobPostingsTab({
  onSelectJob,
}: {
  onSelectJob: (jobId: string) => void;
}) {
  const [search,   setSearch]   = useState('');
  const [status,   setStatus]   = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editJob,  setEditJob]  = useState<JobPostingResponse | null>(null);

  const { data, isLoading } = useJobPostings({
    search:    search || undefined,
    status:    status || undefined,
    page_size: 50,
  });

  const createJob  = useCreateJob();
  const publishJob = usePublishJob();
  const closeJob   = useCloseJob();

  function handleCreate(form: JobPostingCreate) {
    createJob.mutate(form, { onSuccess: () => setShowForm(false) });
  }

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search job postings…"
            className="pl-9"
          />
        </div>
        <Select value={status || 'all'} onValueChange={(v) => setStatus(v === 'all' ? '' : v)}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            {(['draft', 'open', 'closed', 'on_hold', 'filled'] as JobStatus[]).map((s) => (
              <SelectItem key={s} value={s} className="capitalize">{s.replace('_', ' ')}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button onClick={() => setShowForm(true)} className="gap-1.5 shrink-0">
          <Plus className="h-4 w-4" />
          New Posting
        </Button>
      </div>

      {/* Table */}
      <div className="rounded-xl border bg-white overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-slate-50">
              <TableHead>Title</TableHead>
              <TableHead>Department</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-center">Vacancies</TableHead>
              <TableHead className="text-center">Applications</TableHead>
              <TableHead>Closing</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={8} className="text-center text-slate-400 py-12">
                  Loading…
                </TableCell>
              </TableRow>
            )}
            {!isLoading && (data?.results ?? []).length === 0 && (
              <TableRow>
                <TableCell colSpan={8} className="text-center text-slate-400 py-12">
                  No job postings found.
                </TableCell>
              </TableRow>
            )}
            {(data?.results ?? []).map((job) => (
              <TableRow key={job.id} className="hover:bg-slate-50/50">
                <TableCell className="font-medium text-slate-800">{job.title}</TableCell>
                <TableCell className="text-slate-600 text-sm">
                  {job.department_name ?? '—'}
                </TableCell>
                <TableCell>
                  <span className="text-xs capitalize text-slate-600">
                    {job.employment_type.replace('_', ' ')}
                  </span>
                </TableCell>
                <TableCell>
                  <Badge variant="outline" className={`text-xs capitalize ${JOB_STATUS_COLORS[job.status]}`}>
                    {job.status.replace('_', ' ')}
                  </Badge>
                </TableCell>
                <TableCell className="text-center text-sm">{job.vacancies}</TableCell>
                <TableCell className="text-center">
                  <button
                    onClick={() => onSelectJob(job.id)}
                    className="text-sm text-blue-600 hover:underline font-medium"
                  >
                    {job.application_count}
                  </button>
                </TableCell>
                <TableCell className="text-sm text-slate-600">{formatDate(job.closing_date)}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2 text-xs"
                      onClick={() => onSelectJob(job.id)}
                    >
                      <Eye className="h-3.5 w-3.5" />
                    </Button>
                    {job.status === 'draft' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2 text-xs text-green-600 hover:text-green-700"
                        onClick={() => publishJob.mutate(job.id)}
                      >
                        Publish
                      </Button>
                    )}
                    {job.status === 'open' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2 text-xs text-red-600 hover:text-red-700"
                        onClick={() => closeJob.mutate(job.id)}
                      >
                        Close
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Create dialog */}
      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>New Job Posting</DialogTitle>
          </DialogHeader>
          <JobPostingForm
            departments={[]}
            designations={[]}
            onSubmit={handleCreate}
            isSubmitting={createJob.isPending}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Pipeline / Kanban tab ────────────────────────────────────────────────────

function PipelineTab({
  onCardClick,
}: {
  onCardClick: (appId: string) => void;
}) {
  const [selectedJobId, setSelectedJobId] = useState('');
  const { data: jobs } = useJobPostings({ status: 'open', page_size: 100 });

  return (
    <div className="space-y-4">
      {/* Job selector */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-slate-700 shrink-0">Viewing pipeline for:</label>
        <Select value={selectedJobId} onValueChange={setSelectedJobId}>
          <SelectTrigger className="w-72">
            <SelectValue placeholder="Select a job posting…" />
          </SelectTrigger>
          <SelectContent>
            {(jobs?.results ?? []).map((j) => (
              <SelectItem key={j.id} value={j.id}>{j.title}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {!selectedJobId && (
        <div className="flex items-center justify-center h-48 rounded-xl border-2 border-dashed text-slate-400 text-sm">
          Select a job posting above to view its Kanban pipeline.
        </div>
      )}

      {selectedJobId && (
        <KanbanBoard jobId={selectedJobId} onCardClick={onCardClick} />
      )}
    </div>
  );
}

// ─── All Applications tab ─────────────────────────────────────────────────────

function ApplicationsTab({
  onCardClick,
}: {
  onCardClick: (appId: string) => void;
}) {
  const [search, setSearch]   = useState('');
  const [status, setStatus]   = useState('');
  const [minScore, setMinScore] = useState('');

  const { data, isLoading } = useApplications({
    search:        search || undefined,
    status:        (status as ApplicationStatus) || undefined,
    min_ai_score:  minScore ? Number(minScore) : undefined,
    page_size:     50,
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or email…"
            className="pl-9"
          />
        </div>
        <Select value={status || 'all'} onValueChange={(v) => setStatus(v === 'all' ? '' : v)}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All stages" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Stages</SelectItem>
            {(['applied','screening','shortlisted','interview','offered','hired','rejected','withdrawn'] as ApplicationStatus[]).map((s) => (
              <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-400 shrink-0" />
          <Input
            type="number"
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
            placeholder="Min AI score"
            className="w-32"
            min={0}
            max={100}
          />
        </div>
      </div>

      <div className="rounded-xl border bg-white overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-slate-50">
              <TableHead>Candidate</TableHead>
              <TableHead>Position</TableHead>
              <TableHead>Source</TableHead>
              <TableHead>Stage</TableHead>
              <TableHead>AI Score</TableHead>
              <TableHead>Applied</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-slate-400 py-12">Loading…</TableCell>
              </TableRow>
            )}
            {!isLoading && (data?.results ?? []).length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-slate-400 py-12">No applications found.</TableCell>
              </TableRow>
            )}
            {(data?.results ?? []).map((app) => (
              <TableRow
                key={app.id}
                className="hover:bg-slate-50/50 cursor-pointer"
                onClick={() => onCardClick(app.id)}
              >
                <TableCell>
                  <p className="font-medium text-slate-800">{app.candidate_name}</p>
                  <p className="text-xs text-slate-500">{app.candidate_email}</p>
                </TableCell>
                <TableCell className="text-sm text-slate-600">{app.job_title ?? '—'}</TableCell>
                <TableCell>
                  <span className="text-xs capitalize text-slate-600">{app.source.replace('_', ' ')}</span>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary" className={`text-xs capitalize ${APP_STATUS_COLORS[app.status]}`}>
                    {app.status}
                  </Badge>
                </TableCell>
                <TableCell>
                  <AIScoreCard score={app.ai_score} compact />
                </TableCell>
                <TableCell className="text-sm text-slate-600">{formatDate(app.applied_at)}</TableCell>
                <TableCell>
                  <ChevronRight className="h-4 w-4 text-slate-400" />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {data && (
          <div className="px-4 py-2.5 border-t text-xs text-slate-500">
            Showing {data.results.length} of {data.count} applications
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Interviews tab ───────────────────────────────────────────────────────────

function InterviewsTab() {
  const { data: applications } = useApplications({ status: 'interview', page_size: 100 });

  const apps = applications?.results ?? [];

  return (
    <div className="space-y-3">
      {apps.length === 0 && (
        <div className="flex items-center justify-center h-48 rounded-xl border-2 border-dashed text-slate-400 text-sm">
          No candidates are currently in the interview stage.
        </div>
      )}
      {apps.map((app) => (
        <InterviewRow key={app.id} appId={app.id} candidateName={app.candidate_name} />
      ))}
    </div>
  );
}

function InterviewRow({ appId, candidateName }: { appId: string; candidateName: string }) {
  const { data: interviews } = useApplicationInterviews(appId);
  if (!interviews?.length) return null;

  return (
    <div className="rounded-xl border bg-white p-4">
      <p className="font-medium text-slate-800 mb-3">{candidateName}</p>
      <div className="space-y-2">
        {interviews.map((iv) => (
          <div key={iv.id} className="flex items-center gap-3 text-sm">
            <div className={`h-2 w-2 rounded-full shrink-0 ${
              iv.status === 'completed' ? 'bg-green-500' :
              iv.status === 'scheduled' ? 'bg-blue-500' : 'bg-slate-300'
            }`} />
            <span className="text-slate-700 flex-1">
              {iv.title ?? `Round ${iv.round_number}`}
              {iv.interviewer && (
                <span className="text-slate-400"> · {iv.interviewer.full_name}</span>
              )}
            </span>
            <span className="text-slate-500 flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              {iv.scheduled_at ? formatDate(iv.scheduled_at) : 'TBD'}
            </span>
            <Badge variant="outline" className="text-xs capitalize">
              {iv.status.replace('_', ' ')}
            </Badge>
            {iv.rating !== null && (
              <span className="text-xs font-semibold text-amber-600">{iv.rating}/10</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function RecruitmentPage() {
  const [activeTab,        setActiveTab]        = useState('postings');
  const [selectedJobId,    setSelectedJobId]    = useState<string | null>(null);
  const [selectedAppId,    setSelectedAppId]    = useState<string | null>(null);
  const [scheduleAppId,    setScheduleAppId]    = useState<string | null>(null);
  const [offerAppId,       setOfferAppId]       = useState<string | null>(null);

  // For schedule dialog — resolve candidate name from app list
  const { data: selectedApp } = useApplications(
    selectedAppId ? { page_size: 1 } : {},
  );

  // For offer dialog — resolve candidate/job from selected application
  const resolvedApp = selectedApp?.results?.[0];

  // When clicking a job posting → switch to pipeline tab with that job
  function handleSelectJob(jobId: string) {
    setSelectedJobId(jobId);
    setActiveTab('pipeline');
  }

  // When clicking a kanban card or application row
  function handleSelectApp(appId: string) {
    setSelectedAppId(appId);
  }

  return (
    <div className="p-6 space-y-6 max-w-screen-2xl mx-auto">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Recruitment</h1>
          <p className="text-sm text-slate-500 mt-0.5">Manage job postings, candidates, and hiring pipeline</p>
        </div>
      </div>

      {/* Summary cards */}
      <SummaryCards total={0} open={0} applications={0} interviews={0} />

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid grid-cols-4 w-full max-w-lg">
          <TabsTrigger value="postings">
            <Briefcase className="h-4 w-4 mr-1.5" />
            Postings
          </TabsTrigger>
          <TabsTrigger value="pipeline">
            <Users className="h-4 w-4 mr-1.5" />
            Pipeline
          </TabsTrigger>
          <TabsTrigger value="applications">
            <Filter className="h-4 w-4 mr-1.5" />
            Applications
          </TabsTrigger>
          <TabsTrigger value="interviews">
            <Calendar className="h-4 w-4 mr-1.5" />
            Interviews
          </TabsTrigger>
        </TabsList>

        <TabsContent value="postings" className="mt-6">
          <JobPostingsTab onSelectJob={handleSelectJob} />
        </TabsContent>

        <TabsContent value="pipeline" className="mt-6">
          <PipelineTab onCardClick={handleSelectApp} />
        </TabsContent>

        <TabsContent value="applications" className="mt-6">
          <ApplicationsTab onCardClick={handleSelectApp} />
        </TabsContent>

        <TabsContent value="interviews" className="mt-6">
          <InterviewsTab />
        </TabsContent>
      </Tabs>

      {/* Application detail side sheet */}
      <Sheet open={!!selectedAppId} onOpenChange={(open) => !open && setSelectedAppId(null)}>
        <SheetContent side="right" className="w-full sm:w-[480px] p-0">
          {selectedAppId && (
            <ApplicationDetailPanel
              applicationId={selectedAppId}
              onClose={() => setSelectedAppId(null)}
              onSchedule={(id) => {
                setSelectedAppId(null);
                setScheduleAppId(id);
              }}
              onOffer={(id) => {
                setSelectedAppId(null);
                setOfferAppId(id);
              }}
            />
          )}
        </SheetContent>
      </Sheet>

      {/* Schedule interview dialog */}
      {scheduleAppId && (
        <ScheduleInterviewDialog
          open={!!scheduleAppId}
          onOpenChange={(open) => !open && setScheduleAppId(null)}
          applicationId={scheduleAppId}
          candidateName="Candidate"
          interviewers={[]}
        />
      )}

      {/* Offer letter dialog */}
      {offerAppId && (
        <OfferLetterDialog
          open={!!offerAppId}
          onOpenChange={(open) => !open && setOfferAppId(null)}
          applicationId={offerAppId}
          candidateName="Candidate"
          jobTitle="Position"
        />
      )}
    </div>
  );
}
