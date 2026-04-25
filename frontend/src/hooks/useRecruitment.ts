'use client';

/**
 * AI-HRMS — Recruitment module TanStack Query hooks.
 *
 * Query key convention:
 *   ['jobs', filters]                 → paginated job list
 *   ['job', id]                       → single job detail
 *   ['pipeline', jobId]               → kanban pipeline data
 *   ['applications', filters]         → paginated applications
 *   ['application', id]               → single application detail
 *   ['interviews', appId]             → interviews for an application
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as recruitApi     from '@/lib/api/recruitment';
import { extractApiError } from '@/lib/auth';
import type {
  ApplicationFilterParams,
  ApplicationStageUpdate,
  InterviewFeedbackRequest,
  InterviewScheduleRequest,
  JobApplicationCreate,
  JobPostingCreate,
  JobPostingUpdate,
  OfferLetterRequest,
} from '@/types/recruitment';

// ─── Query keys ───────────────────────────────────────────────────────────────

export const recruitKeys = {
  jobs:          (f: Record<string, any>)           => ['jobs', f] as const,
  job:           (id: string)                       => ['job', id] as const,
  pipeline:      (jobId: string)                    => ['pipeline', jobId] as const,
  applications:  (f: Partial<ApplicationFilterParams>) => ['applications', f] as const,
  application:   (id: string)                       => ['application', id] as const,
  interviews:    (appId: string)                    => ['interviews', appId] as const,
};

// ─── Job Postings ─────────────────────────────────────────────────────────────

export function useJobPostings(filters: {
  status?: string;
  department_id?: string;
  employment_type?: string;
  search?: string;
  page?: number;
  page_size?: number;
} = {}) {
  return useQuery({
    queryKey:        recruitKeys.jobs(filters),
    queryFn:         () => recruitApi.getJobPostings(filters),
    staleTime:       30_000,
    placeholderData: (prev) => prev,
  });
}

export function useJobPosting(id: string) {
  return useQuery({
    queryKey:  recruitKeys.job(id),
    queryFn:   () => recruitApi.getJobPosting(id),
    staleTime: 30_000,
    enabled:   !!id,
  });
}

export function usePipelineStats(jobId: string) {
  return useQuery({
    queryKey:  recruitKeys.pipeline(jobId),
    queryFn:   () => recruitApi.getPipelineStats(jobId),
    staleTime: 15_000,
    enabled:   !!jobId,
    refetchInterval: 30_000,
  });
}

export function useCreateJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: JobPostingCreate) => recruitApi.createJobPosting(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['jobs'] });
      toast.success('Job posting created.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

export function useUpdateJob(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: JobPostingUpdate) => recruitApi.updateJobPosting(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['jobs'] });
      qc.invalidateQueries({ queryKey: recruitKeys.job(id) });
      toast.success('Job posting updated.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

export function usePublishJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => recruitApi.publishJobPosting(id),
    onSuccess: (job) => {
      qc.invalidateQueries({ queryKey: ['jobs'] });
      qc.invalidateQueries({ queryKey: recruitKeys.job(job.id) });
      toast.success('Job posting published.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

export function useCloseJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => recruitApi.closeJobPosting(id),
    onSuccess: (job) => {
      qc.invalidateQueries({ queryKey: ['jobs'] });
      qc.invalidateQueries({ queryKey: recruitKeys.job(job.id) });
      toast.success('Job posting closed.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

// ─── Applications ─────────────────────────────────────────────────────────────

export function useApplications(filters: Partial<ApplicationFilterParams> = {}) {
  return useQuery({
    queryKey:        recruitKeys.applications(filters),
    queryFn:         () => recruitApi.getApplications(filters),
    staleTime:       20_000,
    placeholderData: (prev) => prev,
  });
}

export function useApplication(id: string) {
  return useQuery({
    queryKey:  recruitKeys.application(id),
    queryFn:   () => recruitApi.getApplication(id),
    staleTime: 30_000,
    enabled:   !!id,
  });
}

export function useApplyForJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: JobApplicationCreate) => recruitApi.createApplication(data),
    onSuccess: (app) => {
      qc.invalidateQueries({ queryKey: ['applications'] });
      qc.invalidateQueries({ queryKey: recruitKeys.pipeline(app.job_posting_id) });
      toast.success('Application submitted.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

export function useUpdateStage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ApplicationStageUpdate }) =>
      recruitApi.updateApplicationStage(id, data),
    onSuccess: (app) => {
      qc.invalidateQueries({ queryKey: ['applications'] });
      qc.invalidateQueries({ queryKey: recruitKeys.application(app.id) });
      qc.invalidateQueries({ queryKey: recruitKeys.pipeline(app.job_posting_id) });
      toast.success(`Moved to ${app.status}.`);
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

export function useUploadCV() {
  return useMutation({
    mutationFn: (file: File) => recruitApi.uploadCV(file),
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

// ─── Interviews ───────────────────────────────────────────────────────────────

export function useApplicationInterviews(appId: string) {
  return useQuery({
    queryKey: recruitKeys.interviews(appId),
    queryFn:  () => recruitApi.getApplicationInterviews(appId),
    staleTime: 30_000,
    enabled:   !!appId,
  });
}

export function useScheduleInterview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: InterviewScheduleRequest) => recruitApi.scheduleInterview(data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: recruitKeys.interviews(vars.application_id) });
      qc.invalidateQueries({ queryKey: ['applications'] });
      toast.success('Interview scheduled. Invitations sent.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

export function useSubmitFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ interviewId, data }: { interviewId: string; data: InterviewFeedbackRequest }) =>
      recruitApi.submitInterviewFeedback(interviewId, data),
    onSuccess: (iv) => {
      qc.invalidateQueries({ queryKey: recruitKeys.interviews(iv.application_id) });
      toast.success('Feedback submitted.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

// ─── Offers ───────────────────────────────────────────────────────────────────

export function useGenerateOffer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: OfferLetterRequest) => recruitApi.generateOfferLetter(data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: recruitKeys.application(vars.application_id) });
      toast.success('Offer letter generated and sent to candidate.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}
