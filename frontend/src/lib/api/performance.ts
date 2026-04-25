/**
 * AI-HRMS — Performance Management API calls.
 */

import { api } from '@/lib/api';
import type {
  AppraisalCycle,
  AppraisalCycleCreate,
  AppraisalCycleListResponse,
  Appraisal,
  AppraisalListResponse,
  AppraisalFilterParams,
  Goal,
  GoalCreate,
  GoalUpdate,
  GoalsBulkSet,
  SelfReviewSubmit,
  ManagerReviewSubmit,
  BellCurveData,
  TeamPerformanceSummary,
  PIP,
  PIPCreate,
  PIPUpdate,
} from '@/types/performance';

// ─── Appraisal Cycles ─────────────────────────────────────────────────────────

export async function getCycles(page = 1, pageSize = 20): Promise<AppraisalCycleListResponse> {
  const res = await api.get<AppraisalCycleListResponse>(
    `/api/v1/performance/cycles?page=${page}&page_size=${pageSize}`,
  );
  return res.data;
}

export async function getCycle(id: string): Promise<AppraisalCycle> {
  const res = await api.get<AppraisalCycle>(`/api/v1/performance/cycles/${id}`);
  return res.data;
}

export async function createCycle(data: AppraisalCycleCreate): Promise<AppraisalCycle> {
  const res = await api.post<AppraisalCycle>('/api/v1/performance/cycles', data);
  return res.data;
}

export async function launchCycle(id: string): Promise<AppraisalCycle> {
  const res = await api.post<AppraisalCycle>(`/api/v1/performance/cycles/${id}/launch`, {});
  return res.data;
}

export async function closeCycle(id: string): Promise<AppraisalCycle> {
  const res = await api.post<AppraisalCycle>(`/api/v1/performance/cycles/${id}/close`, {});
  return res.data;
}

// ─── Goals ────────────────────────────────────────────────────────────────────

export async function getGoals(employeeId?: string, cycleId?: string): Promise<Goal[]> {
  const p = new URLSearchParams();
  if (employeeId) p.set('employee_id', employeeId);
  if (cycleId)    p.set('cycle_id', cycleId);
  const res = await api.get<Goal[]>(`/api/v1/performance/goals?${p}`);
  return res.data;
}

export async function bulkSetGoals(data: GoalsBulkSet): Promise<Goal[]> {
  const res = await api.put<Goal[]>('/api/v1/performance/goals/bulk', data);
  return res.data;
}

export async function updateGoal(id: string, data: GoalUpdate): Promise<Goal> {
  const res = await api.patch<Goal>(`/api/v1/performance/goals/${id}`, data);
  return res.data;
}

export async function deleteGoal(id: string): Promise<void> {
  await api.delete(`/api/v1/performance/goals/${id}`);
}

// ─── Appraisals ───────────────────────────────────────────────────────────────

export async function getMyAppraisal(): Promise<Appraisal | null> {
  const res = await api.get<Appraisal | null>('/api/v1/performance/appraisals/me');
  return res.data;
}

export async function getAppraisals(filters: Partial<AppraisalFilterParams> = {}): Promise<AppraisalListResponse> {
  const p = new URLSearchParams();
  if (filters.cycle_id)    p.set('cycle_id',    filters.cycle_id);
  if (filters.employee_id) p.set('employee_id', filters.employee_id);
  if (filters.status)      p.set('status',      filters.status);
  if (filters.page)        p.set('page',        String(filters.page));
  if (filters.page_size)   p.set('page_size',   String(filters.page_size));
  const res = await api.get<AppraisalListResponse>(`/api/v1/performance/appraisals?${p}`);
  return res.data;
}

export async function getAppraisal(id: string): Promise<Appraisal> {
  const res = await api.get<Appraisal>(`/api/v1/performance/appraisals/${id}`);
  return res.data;
}

export async function submitSelfReview(id: string, data: SelfReviewSubmit): Promise<Appraisal> {
  const res = await api.post<Appraisal>(`/api/v1/performance/appraisals/${id}/self-review`, data);
  return res.data;
}

export async function submitManagerReview(id: string, data: ManagerReviewSubmit): Promise<Appraisal> {
  const res = await api.post<Appraisal>(`/api/v1/performance/appraisals/${id}/manager-review`, data);
  return res.data;
}

// ─── Bell Curve & Team ────────────────────────────────────────────────────────

export async function getBellCurve(cycleId: string): Promise<BellCurveData> {
  const res = await api.get<BellCurveData>(`/api/v1/performance/cycles/${cycleId}/bell-curve`);
  return res.data;
}

export async function getTeamSummary(cycleId: string): Promise<TeamPerformanceSummary> {
  const res = await api.get<TeamPerformanceSummary>(`/api/v1/performance/cycles/${cycleId}/team`);
  return res.data;
}

// ─── PIPs ─────────────────────────────────────────────────────────────────────

export async function getPips(employeeId?: string): Promise<PIP[]> {
  const p = employeeId ? `?employee_id=${employeeId}` : '';
  const res = await api.get<PIP[]>(`/api/v1/performance/pips${p}`);
  return res.data;
}

export async function createPip(data: PIPCreate): Promise<PIP> {
  const res = await api.post<PIP>('/api/v1/performance/pips', data);
  return res.data;
}

export async function updatePip(id: string, data: PIPUpdate): Promise<PIP> {
  const res = await api.patch<PIP>(`/api/v1/performance/pips/${id}`, data);
  return res.data;
}

export function reportUrl(cycleId: string): string {
  return `/api/v1/performance/cycles/${cycleId}/report`;
}
