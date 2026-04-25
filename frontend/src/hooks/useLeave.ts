'use client';

/**
 * AI-HRMS — Leave module TanStack Query hooks.
 *
 * Query key convention:
 *   ['leave-types']                     → all leave types
 *   ['leave-requests', filters]         → paginated requests
 *   ['leave-balance', employeeId]       → balance for employee
 *   ['leave-balance', 'me']             → my balance
 *   ['leave-calendar', month, year, deptId?] → calendar entries
 *   ['public-holidays', year]           → holidays for year
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as leaveApi       from '@/lib/api/leave';
import { extractApiError } from '@/lib/auth';
import type {
  LeaveFilterParams,
  LeaveRequestCreate,
  LeaveRequestUpdate,
  LeaveApprovalRequest,
  LeaveTypeCreate,
  LeaveTypeUpdate,
  PublicHolidayCreate,
} from '@/types/leave';

// ─── Query keys ───────────────────────────────────────────────────────────────

export const leaveKeys = {
  types:      ()                                      => ['leave-types'] as const,
  requests:   (f: Partial<LeaveFilterParams>)         => ['leave-requests', f] as const,
  balance:    (id: string)                            => ['leave-balance', id] as const,
  myBalance:  ()                                      => ['leave-balance', 'me'] as const,
  calendar:   (m: number, y: number, d?: string)      => ['leave-calendar', m, y, d ?? 'all'] as const,
  holidays:   (year: number)                          => ['public-holidays', year] as const,
};

// ─── Leave Types ──────────────────────────────────────────────────────────────

export function useLeaveTypes() {
  return useQuery({
    queryKey:  leaveKeys.types(),
    queryFn:   leaveApi.getLeaveTypes,
    staleTime: 300_000,
  });
}

export function useCreateLeaveType() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: LeaveTypeCreate) => leaveApi.createLeaveType(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: leaveKeys.types() });
      toast.success('Leave type created.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

export function useUpdateLeaveType(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: LeaveTypeUpdate) => leaveApi.updateLeaveType(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: leaveKeys.types() });
      toast.success('Leave type updated.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

export function useDeleteLeaveType() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => leaveApi.deleteLeaveType(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: leaveKeys.types() });
      toast.success('Leave type deleted.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

// ─── Leave Requests ───────────────────────────────────────────────────────────

export function useLeaveRequests(filters: Partial<LeaveFilterParams> = {}) {
  return useQuery({
    queryKey:        leaveKeys.requests(filters),
    queryFn:         () => leaveApi.getLeaveRequests(filters),
    staleTime:       30_000,
    placeholderData: (prev) => prev,
  });
}

export function useApplyLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: LeaveRequestCreate) => leaveApi.createLeaveRequest(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['leave-requests'] });
      qc.invalidateQueries({ queryKey: ['leave-balance'] });
      toast.success('Leave request submitted successfully.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

export function useUpdateLeaveRequest(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: LeaveRequestUpdate) => leaveApi.updateLeaveRequest(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['leave-requests'] });
      toast.success('Leave request updated.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

export function useCancelLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => leaveApi.cancelLeaveRequest(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['leave-requests'] });
      qc.invalidateQueries({ queryKey: ['leave-balance'] });
      toast.success('Leave request cancelled.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

export function useApproveLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: LeaveApprovalRequest }) =>
      leaveApi.approveLeaveRequest(id, payload),
    onSuccess: (_, { payload }) => {
      qc.invalidateQueries({ queryKey: ['leave-requests'] });
      qc.invalidateQueries({ queryKey: ['leave-balance'] });
      toast.success(payload.action === 'approve' ? 'Leave approved.' : 'Leave rejected.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

// ─── Balance ──────────────────────────────────────────────────────────────────

export function useLeaveBalance(employeeId?: string) {
  return useQuery({
    queryKey:  employeeId ? leaveKeys.balance(employeeId) : leaveKeys.myBalance(),
    queryFn:   () => employeeId
      ? leaveApi.getLeaveBalance(employeeId)
      : leaveApi.getMyLeaveBalance(),
    staleTime: 60_000,
    enabled:   true,
  });
}

export function useMyLeaveBalance() {
  return useQuery({
    queryKey: leaveKeys.myBalance(),
    queryFn:  leaveApi.getMyLeaveBalance,
    staleTime: 60_000,
  });
}

// ─── Calendar ─────────────────────────────────────────────────────────────────

export function useLeaveCalendar(month: number, year: number, departmentId?: string) {
  return useQuery({
    queryKey: leaveKeys.calendar(month, year, departmentId),
    queryFn:  () => leaveApi.getLeaveCalendar({ month, year, department_id: departmentId }),
    staleTime: 60_000,
    enabled:  month >= 1 && month <= 12 && year >= 2000,
  });
}

// ─── Public Holidays ──────────────────────────────────────────────────────────

export function usePublicHolidays(year: number) {
  return useQuery({
    queryKey: leaveKeys.holidays(year),
    queryFn:  () => leaveApi.getPublicHolidays(year),
    staleTime: 3_600_000,  // 1 hour — holidays rarely change
  });
}

export function useCreatePublicHoliday() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: PublicHolidayCreate) => leaveApi.createPublicHoliday(data),
    onSuccess: (_, vars) => {
      const year = new Date(vars.date).getFullYear();
      qc.invalidateQueries({ queryKey: leaveKeys.holidays(year) });
      toast.success('Public holiday added.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

export function useDeletePublicHoliday() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, year }: { id: string; year: number }) =>
      leaveApi.deletePublicHoliday(id).then(() => year),
    onSuccess: (year) => {
      qc.invalidateQueries({ queryKey: leaveKeys.holidays(year) });
      toast.success('Public holiday removed.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}
