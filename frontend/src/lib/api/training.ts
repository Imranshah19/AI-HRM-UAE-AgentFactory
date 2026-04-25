/**
 * AI-HRMS — Training Management API calls.
 */

import { api } from '@/lib/api';
import type {
  TrainingProgram,
  TrainingProgramCreate,
  TrainingProgramUpdate,
  TrainingProgramListResponse,
  TrainingFilterParams,
  TrainingEnrollment,
  EnrollmentCreate,
  EnrollmentUpdate,
  TrainingStats,
} from '@/types/training';

// ─── Stats ────────────────────────────────────────────────────────────────────

export async function getStats(): Promise<TrainingStats> {
  const res = await api.get<TrainingStats>('/api/v1/training/stats');
  return res.data;
}

// ─── Programs ─────────────────────────────────────────────────────────────────

export async function getPrograms(
  filters: Partial<TrainingFilterParams> = {},
): Promise<TrainingProgramListResponse> {
  const p = new URLSearchParams();
  if (filters.status)       p.set('status',       filters.status);
  if (filters.category)     p.set('category',     filters.category);
  if (filters.search)       p.set('search',       filters.search);
  if (filters.is_mandatory !== undefined) p.set('is_mandatory', String(filters.is_mandatory));
  if (filters.page)         p.set('page',         String(filters.page));
  if (filters.page_size)    p.set('page_size',    String(filters.page_size));
  const res = await api.get<TrainingProgramListResponse>(`/api/v1/training/programs?${p}`);
  return res.data;
}

export async function getProgram(id: string): Promise<TrainingProgram> {
  const res = await api.get<TrainingProgram>(`/api/v1/training/programs/${id}`);
  return res.data;
}

export async function createProgram(data: TrainingProgramCreate): Promise<TrainingProgram> {
  const res = await api.post<TrainingProgram>('/api/v1/training/programs', data);
  return res.data;
}

export async function updateProgram(id: string, data: TrainingProgramUpdate): Promise<TrainingProgram> {
  const res = await api.patch<TrainingProgram>(`/api/v1/training/programs/${id}`, data);
  return res.data;
}

export async function deleteProgram(id: string): Promise<void> {
  await api.delete(`/api/v1/training/programs/${id}`);
}

export async function changeStatus(id: string, newStatus: string): Promise<TrainingProgram> {
  const res = await api.post<TrainingProgram>(
    `/api/v1/training/programs/${id}/status?new_status=${encodeURIComponent(newStatus)}`,
    {},
  );
  return res.data;
}

// ─── Enrollments ──────────────────────────────────────────────────────────────

export async function getEnrollments(programId: string): Promise<TrainingEnrollment[]> {
  const res = await api.get<TrainingEnrollment[]>(
    `/api/v1/training/programs/${programId}/enrollments`,
  );
  return res.data;
}

export async function enrollEmployees(
  programId: string,
  data: EnrollmentCreate,
): Promise<TrainingEnrollment[]> {
  const res = await api.post<TrainingEnrollment[]>(
    `/api/v1/training/programs/${programId}/enroll`,
    data,
  );
  return res.data;
}

export async function updateEnrollment(
  enrollmentId: string,
  data: EnrollmentUpdate,
): Promise<TrainingEnrollment> {
  const res = await api.patch<TrainingEnrollment>(
    `/api/v1/training/enrollments/${enrollmentId}`,
    data,
  );
  return res.data;
}

export async function getMyEnrollments(): Promise<TrainingEnrollment[]> {
  const res = await api.get<TrainingEnrollment[]>('/api/v1/training/my');
  return res.data;
}
