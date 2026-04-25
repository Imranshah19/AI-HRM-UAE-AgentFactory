'use client';

/**
 * AI-HRMS — Performance Management TanStack Query hooks.
 *
 * Query key factory:
 *   performanceKeys.cycles(page)
 *   performanceKeys.cycle(id)
 *   performanceKeys.goals(empId, cycleId)
 *   performanceKeys.myAppraisal()
 *   performanceKeys.appraisals(filters)
 *   performanceKeys.appraisal(id)
 *   performanceKeys.bellCurve(cycleId)
 *   performanceKeys.team(cycleId)
 *   performanceKeys.pips(empId)
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as perfApi        from '@/lib/api/performance';
import { extractApiError } from '@/lib/auth';
import type {
  AppraisalCycleCreate,
  AppraisalFilterParams,
  GoalUpdate,
  GoalsBulkSet,
  ManagerReviewSubmit,
  PIPCreate,
  PIPUpdate,
  SelfReviewSubmit,
} from '@/types/performance';

// ─── Query keys ───────────────────────────────────────────────────────────────

export const performanceKeys = {
  cycles:      (page?: number)                          => ['perf-cycles', page] as const,
  cycle:       (id: string)                             => ['perf-cycle', id] as const,
  goals:       (empId?: string, cycleId?: string)       => ['perf-goals', empId, cycleId] as const,
  myAppraisal: ()                                       => ['perf-my-appraisal'] as const,
  appraisals:  (f: Partial<AppraisalFilterParams>)      => ['perf-appraisals', f] as const,
  appraisal:   (id: string)                             => ['perf-appraisal', id] as const,
  bellCurve:   (cycleId: string)                        => ['perf-bell-curve', cycleId] as const,
  team:        (cycleId: string)                        => ['perf-team', cycleId] as const,
  pips:        (empId?: string)                         => ['perf-pips', empId] as const,
};

// ─── Cycles ───────────────────────────────────────────────────────────────────

export function useCycles(page = 1) {
  return useQuery({
    queryKey:        performanceKeys.cycles(page),
    queryFn:         () => perfApi.getCycles(page),
    staleTime:       30_000,
    placeholderData: (prev) => prev,
  });
}

export function useCycle(id: string) {
  return useQuery({
    queryKey: performanceKeys.cycle(id),
    queryFn:  () => perfApi.getCycle(id),
    enabled:  !!id,
  });
}

export function useCreateCycle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AppraisalCycleCreate) => perfApi.createCycle(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['perf-cycles'] });
      toast.success('Appraisal cycle created');
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}

export function useLaunchCycle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => perfApi.launchCycle(id),
    onSuccess: (cycle) => {
      qc.invalidateQueries({ queryKey: ['perf-cycles'] });
      qc.invalidateQueries({ queryKey: performanceKeys.cycle(cycle.id) });
      toast.success(`Cycle "${cycle.name}" launched — appraisals created`);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}

export function useCloseCycle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => perfApi.closeCycle(id),
    onSuccess: (cycle) => {
      qc.invalidateQueries({ queryKey: ['perf-cycles'] });
      qc.invalidateQueries({ queryKey: performanceKeys.cycle(cycle.id) });
      toast.success(`Cycle "${cycle.name}" closed`);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}

// ─── Goals ────────────────────────────────────────────────────────────────────

export function useGoals(employeeId?: string, cycleId?: string) {
  return useQuery({
    queryKey: performanceKeys.goals(employeeId, cycleId),
    queryFn:  () => perfApi.getGoals(employeeId, cycleId),
    enabled:  true,
  });
}

export function useBulkSetGoals() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: GoalsBulkSet) => perfApi.bulkSetGoals(data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: performanceKeys.goals(String(vars.employee_id), String(vars.cycle_id)) });
      toast.success('Goals saved');
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}

export function useUpdateGoal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: GoalUpdate }) =>
      perfApi.updateGoal(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['perf-goals'] });
      toast.success('Goal updated');
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}

export function useDeleteGoal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => perfApi.deleteGoal(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['perf-goals'] });
      toast.success('Goal deleted');
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}

// ─── Appraisals ───────────────────────────────────────────────────────────────

export function useMyAppraisal() {
  return useQuery({
    queryKey: performanceKeys.myAppraisal(),
    queryFn:  () => perfApi.getMyAppraisal(),
    staleTime: 30_000,
  });
}

export function useAppraisals(filters: Partial<AppraisalFilterParams> = {}) {
  return useQuery({
    queryKey:        performanceKeys.appraisals(filters),
    queryFn:         () => perfApi.getAppraisals(filters),
    staleTime:       15_000,
    placeholderData: (prev) => prev,
  });
}

export function useAppraisal(id: string) {
  return useQuery({
    queryKey: performanceKeys.appraisal(id),
    queryFn:  () => perfApi.getAppraisal(id),
    enabled:  !!id,
  });
}

export function useSubmitSelfReview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: SelfReviewSubmit }) =>
      perfApi.submitSelfReview(id, data),
    onSuccess: (appraisal) => {
      qc.invalidateQueries({ queryKey: performanceKeys.myAppraisal() });
      qc.invalidateQueries({ queryKey: performanceKeys.appraisal(appraisal.id) });
      qc.invalidateQueries({ queryKey: ['perf-appraisals'] });
      toast.success('Self review submitted');
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}

export function useSubmitManagerReview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ManagerReviewSubmit }) =>
      perfApi.submitManagerReview(id, data),
    onSuccess: (appraisal) => {
      qc.invalidateQueries({ queryKey: performanceKeys.appraisal(appraisal.id) });
      qc.invalidateQueries({ queryKey: ['perf-appraisals'] });
      qc.invalidateQueries({ queryKey: ['perf-team'] });
      toast.success('Manager review submitted');
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}

// ─── Bell Curve & Team ────────────────────────────────────────────────────────

export function useBellCurve(cycleId: string) {
  return useQuery({
    queryKey: performanceKeys.bellCurve(cycleId),
    queryFn:  () => perfApi.getBellCurve(cycleId),
    enabled:  !!cycleId,
    staleTime: 60_000,
  });
}

export function useTeamSummary(cycleId: string) {
  return useQuery({
    queryKey: performanceKeys.team(cycleId),
    queryFn:  () => perfApi.getTeamSummary(cycleId),
    enabled:  !!cycleId,
    staleTime: 30_000,
  });
}

// ─── PIPs ─────────────────────────────────────────────────────────────────────

export function usePips(employeeId?: string) {
  return useQuery({
    queryKey: performanceKeys.pips(employeeId),
    queryFn:  () => perfApi.getPips(employeeId),
    staleTime: 30_000,
  });
}

export function useCreatePip() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: PIPCreate) => perfApi.createPip(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['perf-pips'] });
      toast.success('PIP created');
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}

export function useUpdatePip() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PIPUpdate }) =>
      perfApi.updatePip(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['perf-pips'] });
      toast.success('PIP updated');
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}
