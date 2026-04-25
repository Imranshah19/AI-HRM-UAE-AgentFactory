/**
 * AI-HRMS — Reports & Analytics API calls.
 */

import { api } from '@/lib/api';
import type {
  AttendanceReport,
  DashboardStats,
  HeadcountReport,
  LeaveReport,
  PayrollReport,
  RecruitmentReport,
  TurnoverReport,
} from '@/types/reports';

export async function getDashboardStats(): Promise<DashboardStats> {
  const res = await api.get<DashboardStats>('/api/v1/reports/dashboard-stats');
  return res.data;
}

export async function getHeadcountReport(): Promise<HeadcountReport> {
  const res = await api.get<HeadcountReport>('/api/v1/reports/headcount');
  return res.data;
}

export async function getTurnoverReport(year: number): Promise<TurnoverReport> {
  const res = await api.get<TurnoverReport>(`/api/v1/reports/turnover?year=${year}`);
  return res.data;
}

export async function getAttendanceReport(month: number, year: number): Promise<AttendanceReport> {
  const res = await api.get<AttendanceReport>(`/api/v1/reports/attendance?month=${month}&year=${year}`);
  return res.data;
}

export async function getPayrollReport(year: number): Promise<PayrollReport> {
  const res = await api.get<PayrollReport>(`/api/v1/reports/payroll?year=${year}`);
  return res.data;
}

export async function getLeaveReport(year: number): Promise<LeaveReport> {
  const res = await api.get<LeaveReport>(`/api/v1/reports/leave?year=${year}`);
  return res.data;
}

export async function getRecruitmentReport(year: number): Promise<RecruitmentReport> {
  const res = await api.get<RecruitmentReport>(`/api/v1/reports/recruitment?year=${year}`);
  return res.data;
}

export function exportUrl(
  type: 'headcount' | 'turnover' | 'attendance' | 'payroll' | 'leave' | 'recruitment',
  params: Record<string, string | number> = {},
): string {
  const p = new URLSearchParams({ export: 'excel' });
  Object.entries(params).forEach(([k, v]) => p.set(k, String(v)));
  return `/api/v1/reports/${type}?${p}`;
}
