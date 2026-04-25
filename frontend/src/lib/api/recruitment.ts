/**
 * AI-HRMS — Recruitment / ATS API calls.
 */

import { api } from '@/lib/api';
import type {
  ApplicationFilterParams,
  ApplicationListResponse,
  ApplicationStageUpdate,
  CVUploadResponse,
  Interview,
  InterviewFeedbackRequest,
  InterviewScheduleRequest,
  JobApplication,
  JobApplicationCreate,
  JobPostingCreate,
  JobPostingListResponse,
  JobPostingResponse,
  JobPostingUpdate,
  OfferLetterRequest,
  PipelineStats,
} from '@/types/recruitment';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function buildParams(filters: Partial<ApplicationFilterParams>): URLSearchParams {
  const p = new URLSearchParams();
  const entries: Array<[string, string | number | undefined]> = [
    ['job_posting_id', filters.job_posting_id],
    ['status',         filters.status],
    ['source',         filters.source],
    ['date_from',      filters.date_from],
    ['date_to',        filters.date_to],
    ['min_ai_score',   filters.min_ai_score],
    ['search',         filters.search],
    ['page',           filters.page],
    ['page_size',      filters.page_size],
  ];
  entries.forEach(([k, v]) => {
    if (v !== undefined && v !== '' && v !== null) p.set(k, String(v));
  });
  return p;
}

// ─── Job Postings ─────────────────────────────────────────────────────────────

export async function getJobPostings(filters: {
  status?: string;
  department_id?: string;
  employment_type?: string;
  search?: string;
  page?: number;
  page_size?: number;
} = {}): Promise<JobPostingListResponse> {
  const p = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== '' && v !== null) p.set(k, String(v));
  });
  const res = await api.get<JobPostingListResponse>(
    `/api/v1/recruitment/jobs?${p.toString()}`,
  );
  return res.data;
}

export async function getJobPosting(id: string): Promise<JobPostingResponse> {
  const res = await api.get<JobPostingResponse>(`/api/v1/recruitment/jobs/${id}`);
  return res.data;
}

export async function createJobPosting(data: JobPostingCreate): Promise<JobPostingResponse> {
  const res = await api.post<JobPostingResponse>('/api/v1/recruitment/jobs', data);
  return res.data;
}

export async function updateJobPosting(
  id: string, data: JobPostingUpdate,
): Promise<JobPostingResponse> {
  const res = await api.patch<JobPostingResponse>(`/api/v1/recruitment/jobs/${id}`, data);
  return res.data;
}

export async function publishJobPosting(id: string): Promise<JobPostingResponse> {
  const res = await api.post<JobPostingResponse>(`/api/v1/recruitment/jobs/${id}/publish`, {});
  return res.data;
}

export async function closeJobPosting(id: string): Promise<JobPostingResponse> {
  const res = await api.post<JobPostingResponse>(`/api/v1/recruitment/jobs/${id}/close`, {});
  return res.data;
}

export async function getPipelineStats(jobId: string): Promise<PipelineStats> {
  const res = await api.get<PipelineStats>(`/api/v1/recruitment/jobs/${jobId}/pipeline`);
  return res.data;
}

// ─── Applications ─────────────────────────────────────────────────────────────

export async function getApplications(
  filters: Partial<ApplicationFilterParams> = {},
): Promise<ApplicationListResponse> {
  const params = buildParams(filters);
  const res    = await api.get<ApplicationListResponse>(
    `/api/v1/recruitment/applications?${params.toString()}`,
  );
  return res.data;
}

export async function getApplication(id: string): Promise<JobApplication> {
  const res = await api.get<JobApplication>(`/api/v1/recruitment/applications/${id}`);
  return res.data;
}

export async function createApplication(
  data: JobApplicationCreate,
): Promise<JobApplication> {
  const res = await api.post<JobApplication>('/api/v1/recruitment/applications', data);
  return res.data;
}

export async function updateApplicationStage(
  id: string, data: ApplicationStageUpdate,
): Promise<JobApplication> {
  const res = await api.patch<JobApplication>(
    `/api/v1/recruitment/applications/${id}/stage`, data,
  );
  return res.data;
}

export async function uploadCV(file: File): Promise<CVUploadResponse> {
  const form = new FormData();
  form.append('file', file);
  const res = await api.post<CVUploadResponse>(
    '/api/v1/recruitment/applications/upload-cv', form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return res.data;
}

// ─── Interviews ───────────────────────────────────────────────────────────────

export async function scheduleInterview(
  data: InterviewScheduleRequest,
): Promise<Interview[]> {
  const res = await api.post<Interview[]>('/api/v1/recruitment/interviews', data);
  return res.data;
}

export async function submitInterviewFeedback(
  interviewId: string, data: InterviewFeedbackRequest,
): Promise<Interview> {
  const res = await api.post<Interview>(
    `/api/v1/recruitment/interviews/${interviewId}/feedback`, data,
  );
  return res.data;
}

export async function getApplicationInterviews(
  appId: string,
): Promise<Interview[]> {
  const res = await api.get<Interview[]>(
    `/api/v1/recruitment/applications/${appId}/interviews`,
  );
  return res.data;
}

// ─── Offers ───────────────────────────────────────────────────────────────────

export async function generateOfferLetter(
  data: OfferLetterRequest,
): Promise<{ offer_url: string }> {
  const res = await api.post<{ offer_url: string }>('/api/v1/recruitment/offers', data);
  return res.data;
}

export function getOfferLetterUrl(appId: string): string {
  return `/api/v1/recruitment/offers/${appId}`;
}

// ─── Public ───────────────────────────────────────────────────────────────────

export async function getPublicJobs(filters: {
  employment_type?: string;
  search?: string;
} = {}): Promise<JobPostingResponse[]> {
  const p = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== '') p.set(k, String(v));
  });
  const res = await api.get<JobPostingResponse[]>(`/api/v1/public/jobs?${p.toString()}`);
  return res.data;
}

export async function publicApply(
  jobId: string, data: JobApplicationCreate,
): Promise<{ message: string; application_id: string }> {
  const res = await api.post<{ message: string; application_id: string }>(
    `/api/v1/public/jobs/${jobId}/apply`, data,
  );
  return res.data;
}
