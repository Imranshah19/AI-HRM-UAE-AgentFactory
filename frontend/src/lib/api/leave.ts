/**
 * AI-HRMS — Leave module API calls.
 */

import { api } from '@/lib/api';
import type {
  LeaveType,
  LeaveTypeCreate,
  LeaveTypeUpdate,
  LeaveRequest,
  LeaveRequestCreate,
  LeaveRequestUpdate,
  LeaveApprovalRequest,
  LeaveBalanceResponse,
  LeaveCalendarEntry,
  LeaveFilterParams,
  PaginatedLeaveRequests,
  PublicHoliday,
  PublicHolidayCreate,
} from '@/types/leave';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function buildParams(filters: Partial<LeaveFilterParams>): URLSearchParams {
  const p = new URLSearchParams();
  const entries: Array<[string, string | number | undefined]> = [
    ['employee_id',   filters.employee_id],
    ['department_id', filters.department_id],
    ['leave_type_id', filters.leave_type_id],
    ['status',        filters.status],
    ['start_date',    filters.start_date],
    ['end_date',      filters.end_date],
    ['page',          filters.page],
    ['page_size',     filters.page_size],
  ];
  entries.forEach(([k, v]) => {
    if (v !== undefined && v !== '' && v !== null) p.set(k, String(v));
  });
  return p;
}

// ─── Leave Types ──────────────────────────────────────────────────────────────

export async function getLeaveTypes(): Promise<LeaveType[]> {
  const res = await api.get<LeaveType[]>('/api/v1/leave/types');
  return res.data;
}

export async function createLeaveType(data: LeaveTypeCreate): Promise<LeaveType> {
  const res = await api.post<LeaveType>('/api/v1/leave/types', data);
  return res.data;
}

export async function updateLeaveType(id: string, data: LeaveTypeUpdate): Promise<LeaveType> {
  const res = await api.patch<LeaveType>(`/api/v1/leave/types/${id}`, data);
  return res.data;
}

export async function deleteLeaveType(id: string): Promise<void> {
  await api.delete(`/api/v1/leave/types/${id}`);
}

// ─── Leave Requests ───────────────────────────────────────────────────────────

export async function getLeaveRequests(
  filters: Partial<LeaveFilterParams> = {},
): Promise<PaginatedLeaveRequests> {
  const params = buildParams(filters);
  const res    = await api.get<PaginatedLeaveRequests>(
    `/api/v1/leave/requests?${params.toString()}`,
  );
  return res.data;
}

export async function getLeaveRequest(id: string): Promise<LeaveRequest> {
  const res = await api.get<LeaveRequest>(`/api/v1/leave/requests/${id}`);
  return res.data;
}

export async function createLeaveRequest(data: LeaveRequestCreate): Promise<LeaveRequest> {
  const res = await api.post<LeaveRequest>('/api/v1/leave/requests', data);
  return res.data;
}

export async function updateLeaveRequest(
  id: string, data: LeaveRequestUpdate,
): Promise<LeaveRequest> {
  const res = await api.patch<LeaveRequest>(`/api/v1/leave/requests/${id}`, data);
  return res.data;
}

export async function cancelLeaveRequest(id: string): Promise<LeaveRequest> {
  const res = await api.delete<LeaveRequest>(`/api/v1/leave/requests/${id}`);
  return res.data;
}

// ─── Approval ─────────────────────────────────────────────────────────────────

export async function approveLeaveRequest(
  id: string, payload: LeaveApprovalRequest,
): Promise<LeaveRequest> {
  const res = await api.post<LeaveRequest>(`/api/v1/leave/requests/${id}/approve`, payload);
  return res.data;
}

// ─── Balance ──────────────────────────────────────────────────────────────────

export async function getLeaveBalance(employeeId: string): Promise<LeaveBalanceResponse> {
  const res = await api.get<LeaveBalanceResponse>(`/api/v1/leave/balance/${employeeId}`);
  return res.data;
}

export async function getMyLeaveBalance(): Promise<LeaveBalanceResponse> {
  const res = await api.get<LeaveBalanceResponse>('/api/v1/leave/balance/me');
  return res.data;
}

// ─── Calendar ─────────────────────────────────────────────────────────────────

export async function getLeaveCalendar(params: {
  month: number;
  year:  number;
  department_id?: string;
}): Promise<LeaveCalendarEntry[]> {
  const p = new URLSearchParams({
    month: String(params.month),
    year:  String(params.year),
    ...(params.department_id ? { department_id: params.department_id } : {}),
  });
  const res = await api.get<LeaveCalendarEntry[]>(`/api/v1/leave/calendar?${p.toString()}`);
  return res.data;
}

// ─── Public Holidays ──────────────────────────────────────────────────────────

export async function getPublicHolidays(year: number): Promise<PublicHoliday[]> {
  const res = await api.get<PublicHoliday[]>(`/api/v1/leave/holidays?year=${year}`);
  return res.data;
}

export async function createPublicHoliday(data: PublicHolidayCreate): Promise<PublicHoliday> {
  const res = await api.post<PublicHoliday>('/api/v1/leave/holidays', data);
  return res.data;
}

export async function deletePublicHoliday(id: string): Promise<void> {
  await api.delete(`/api/v1/leave/holidays/${id}`);
}
