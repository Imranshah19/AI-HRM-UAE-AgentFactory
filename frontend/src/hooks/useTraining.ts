'use client';

/**
 * AI-HRMS — Training Management TanStack Query hooks.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as trainingApi    from '@/lib/api/training';
import { extractApiError } from '@/lib/auth';
import type {
  EnrollmentCreate,
  EnrollmentUpdate,
  TrainingFilterParams,
  TrainingProgramCreate,
  TrainingProgramUpdate,
} from '@/types/training';

// ─── Query keys ───────────────────────────────────────────────────────────────

export const trainingKeys = {
  stats:       ()                                         => ['training-stats'] as const,
  programs:    (f: Partial<TrainingFilterParams>)         => ['training-programs', f] as const,
  program:     (id: string)                               => ['training-program', id] as const,
  enrollments: (programId: string)                        => ['training-enrollments', programId] as const,
  my:          ()                                         => ['training-my'] as const,
};

// ─── Stats ────────────────────────────────────────────────────────────────────

export function useTrainingStats() {
  return useQuery({
    queryKey: trainingKeys.stats(),
    queryFn:  () => trainingApi.getStats(),
    staleTime: 60_000,
  });
}

// ─── Programs ─────────────────────────────────────────────────────────────────

export function usePrograms(filters: Partial<TrainingFilterParams> = {}) {
  return useQuery({
    queryKey:        trainingKeys.programs(filters),
    queryFn:         () => trainingApi.getPrograms(filters),
    staleTime:       15_000,
    placeholderData: (prev) => prev,
  });
}

export function useProgram(id: string) {
  return useQuery({
    queryKey: trainingKeys.program(id),
    queryFn:  () => trainingApi.getProgram(id),
    enabled:  !!id,
  });
}

export function useCreateProgram() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TrainingProgramCreate) => trainingApi.createProgram(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['training-programs'] });
      qc.invalidateQueries({ queryKey: ['training-stats'] });
      toast.success('Training program created');
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}

export function useUpdateProgram() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: TrainingProgramUpdate }) =>
      trainingApi.updateProgram(id, data),
    onSuccess: (program) => {
      qc.invalidateQueries({ queryKey: ['training-programs'] });
      qc.invalidateQueries({ queryKey: trainingKeys.program(program.id) });
      toast.success('Program updated');
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}

export function useDeleteProgram() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => trainingApi.deleteProgram(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['training-programs'] });
      qc.invalidateQueries({ queryKey: ['training-stats'] });
      toast.success('Program deleted');
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}

export function useChangeStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, newStatus }: { id: string; newStatus: string }) =>
      trainingApi.changeStatus(id, newStatus),
    onSuccess: (program) => {
      qc.invalidateQueries({ queryKey: ['training-programs'] });
      qc.invalidateQueries({ queryKey: trainingKeys.program(program.id) });
      qc.invalidateQueries({ queryKey: ['training-stats'] });
      toast.success(`Status changed to "${program.status.replace(/_/g, ' ')}"`);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}

// ─── Enrollments ──────────────────────────────────────────────────────────────

export function useEnrollments(programId: string) {
  return useQuery({
    queryKey: trainingKeys.enrollments(programId),
    queryFn:  () => trainingApi.getEnrollments(programId),
    enabled:  !!programId,
  });
}

export function useEnrollEmployees() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ programId, data }: { programId: string; data: EnrollmentCreate }) =>
      trainingApi.enrollEmployees(programId, data),
    onSuccess: (_, { programId }) => {
      qc.invalidateQueries({ queryKey: trainingKeys.enrollments(programId) });
      qc.invalidateQueries({ queryKey: ['training-programs'] });
      toast.success('Employees enrolled');
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}

export function useUpdateEnrollment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: EnrollmentUpdate }) =>
      trainingApi.updateEnrollment(id, data),
    onSuccess: (enrollment) => {
      qc.invalidateQueries({ queryKey: trainingKeys.enrollments(enrollment.program_id) });
      qc.invalidateQueries({ queryKey: ['training-my'] });
      qc.invalidateQueries({ queryKey: ['training-stats'] });
      toast.success('Enrollment updated');
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}

export function useMyEnrollments() {
  return useQuery({
    queryKey: trainingKeys.my(),
    queryFn:  () => trainingApi.getMyEnrollments(),
    staleTime: 30_000,
  });
}
