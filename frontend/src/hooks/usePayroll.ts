'use client';

/**
 * AI-HRMS — Payroll module TanStack Query hooks.
 *
 * Query key convention:
 *   ['payroll-runs', filters]          → paginated run list
 *   ['payroll-run', id]                → single run + records
 *   ['payslips', 'me']                 → my payslip history
 *   ['payslips', 'employee', id]       → employee payslip history
 *   ['salary-preview', id, month, yr]  → what-if preview
 *   ['tax-slabs', year]                → tax slabs for year
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as payrollApi      from '@/lib/api/payroll';
import { extractApiError }  from '@/lib/auth';
import type {
  PayrollFilterParams,
  PayrollRunCreate,
  PayrollApprovalRequest,
  TaxSlabCreate,
  TaxSlabUpdate,
} from '@/types/payroll';

// ─── Query keys ───────────────────────────────────────────────────────────────

export const payrollKeys = {
  runs:          (f: Partial<PayrollFilterParams>)       => ['payroll-runs', f] as const,
  run:           (id: string)                            => ['payroll-run', id] as const,
  myPayslips:    ()                                      => ['payslips', 'me'] as const,
  empPayslips:   (id: string)                            => ['payslips', 'employee', id] as const,
  preview:       (id: string, m: number, y: number)     => ['salary-preview', id, m, y] as const,
  taxSlabs:      (year: number)                          => ['tax-slabs', year] as const,
};

// ─── Payroll Runs ─────────────────────────────────────────────────────────────

export function usePayrollRuns(filters: Partial<PayrollFilterParams> = {}) {
  return useQuery({
    queryKey:        payrollKeys.runs(filters),
    queryFn:         () => payrollApi.getPayrollRuns(filters),
    staleTime:       15_000,
    placeholderData: (prev) => prev,
  });
}

export function usePayrollRun(id: string, options?: { enabled?: boolean; refetchInterval?: number }) {
  return useQuery({
    queryKey:       payrollKeys.run(id),
    queryFn:        () => payrollApi.getPayrollRun(id),
    staleTime:      10_000,
    enabled:        !!id && (options?.enabled ?? true),
    refetchInterval: options?.refetchInterval,
  });
}

// ─── Mutations ────────────────────────────────────────────────────────────────

export function useRunPayroll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: PayrollRunCreate) => payrollApi.createPayrollRun(data),
    onSuccess: (run) => {
      qc.invalidateQueries({ queryKey: ['payroll-runs'] });
      toast.success(`Payroll run started for ${run.label ?? `${run.month}/${run.year}`}.`);
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

export function useApprovePayroll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: PayrollApprovalRequest }) =>
      payrollApi.approvePayrollRun(id, payload),
    onSuccess: (run) => {
      qc.invalidateQueries({ queryKey: ['payroll-runs'] });
      qc.invalidateQueries({ queryKey: payrollKeys.run(run.id) });
      toast.success('Payroll run approved. Payslips are being generated.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

export function useRejectPayroll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: PayrollApprovalRequest }) =>
      payrollApi.rejectPayrollRun(id, payload),
    onSuccess: (run) => {
      qc.invalidateQueries({ queryKey: ['payroll-runs'] });
      qc.invalidateQueries({ queryKey: payrollKeys.run(run.id) });
      toast.success('Payroll run rejected and records removed.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

// ─── Payslips ─────────────────────────────────────────────────────────────────

export function useMyPayslips() {
  return useQuery({
    queryKey: payrollKeys.myPayslips(),
    queryFn:  payrollApi.getMyPayslips,
    staleTime: 60_000,
  });
}

export function useEmployeePayslips(employeeId?: string) {
  return useQuery({
    queryKey: payrollKeys.empPayslips(employeeId ?? ''),
    queryFn:  () => payrollApi.getEmployeePayslips(employeeId!),
    staleTime: 60_000,
    enabled:  !!employeeId,
  });
}

// ─── Salary Preview ───────────────────────────────────────────────────────────

export function useSalaryPreview(
  employeeId: string,
  month: number,
  year: number,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: payrollKeys.preview(employeeId, month, year),
    queryFn:  () => payrollApi.getSalaryPreview(employeeId, month, year),
    staleTime: 30_000,
    enabled:  !!employeeId && month >= 1 && month <= 12 && year >= 2020
              && (options?.enabled ?? true),
  });
}

// ─── Tax Slabs ────────────────────────────────────────────────────────────────

export function useTaxSlabs(year: number) {
  return useQuery({
    queryKey: payrollKeys.taxSlabs(year),
    queryFn:  () => payrollApi.getTaxSlabs(year),
    staleTime: 300_000,
  });
}

export function useCreateTaxSlab(year: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TaxSlabCreate) => payrollApi.createTaxSlab(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: payrollKeys.taxSlabs(year) });
      toast.success('Tax slab added.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

export function useUpdateTaxSlab(year: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: TaxSlabUpdate }) =>
      payrollApi.updateTaxSlab(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: payrollKeys.taxSlabs(year) });
      toast.success('Tax slab updated.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}
