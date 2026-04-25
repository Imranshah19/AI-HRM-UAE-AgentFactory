'use client';

/**
 * AI-HRMS — Reports TanStack Query hooks.
 */

import { useQuery } from '@tanstack/react-query';

import * as reportsApi from '@/lib/api/reports';

export const reportKeys = {
  dashboardStats: ()                          => ['reports', 'dashboard-stats'] as const,
  headcount:      ()                          => ['reports', 'headcount'] as const,
  turnover:       (year: number)              => ['reports', 'turnover', year] as const,
  attendance:     (month: number, year: number) => ['reports', 'attendance', month, year] as const,
  payroll:        (year: number)              => ['reports', 'payroll', year] as const,
  leave:          (year: number)              => ['reports', 'leave', year] as const,
  recruitment:    (year: number)              => ['reports', 'recruitment', year] as const,
};

export function useDashboardStats() {
  return useQuery({
    queryKey: reportKeys.dashboardStats(),
    queryFn:  () => reportsApi.getDashboardStats(),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useHeadcountReport() {
  return useQuery({
    queryKey: reportKeys.headcount(),
    queryFn:  () => reportsApi.getHeadcountReport(),
    staleTime: 60_000,
  });
}

export function useTurnoverReport(year: number) {
  return useQuery({
    queryKey: reportKeys.turnover(year),
    queryFn:  () => reportsApi.getTurnoverReport(year),
    staleTime: 60_000,
  });
}

export function useAttendanceReport(month: number, year: number) {
  return useQuery({
    queryKey: reportKeys.attendance(month, year),
    queryFn:  () => reportsApi.getAttendanceReport(month, year),
    staleTime: 60_000,
  });
}

export function usePayrollReport(year: number) {
  return useQuery({
    queryKey: reportKeys.payroll(year),
    queryFn:  () => reportsApi.getPayrollReport(year),
    staleTime: 60_000,
  });
}

export function useLeaveReport(year: number) {
  return useQuery({
    queryKey: reportKeys.leave(year),
    queryFn:  () => reportsApi.getLeaveReport(year),
    staleTime: 60_000,
  });
}

export function useRecruitmentReport(year: number) {
  return useQuery({
    queryKey: reportKeys.recruitment(year),
    queryFn:  () => reportsApi.getRecruitmentReport(year),
    staleTime: 60_000,
  });
}
