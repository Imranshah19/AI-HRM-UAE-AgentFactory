/**
 * AI-HRMS — Attendance module API calls.
 */

import { api } from '@/lib/api';
import type {
  Shift,
  ShiftCreate,
  AttendanceRecord,
  AttendanceRecordListItem,
  PaginatedAttendanceRecords,
  AttendanceCheckInRequest,
  AttendanceCheckOutRequest,
  AttendanceManualEntryRequest,
  AttendanceAdjustmentRequest,
  AdjustmentRecord,
  AttendanceSummary,
  TimesheetResponse,
  LiveAttendanceEntry,
  AttendanceFilterParams,
} from '@/types/attendance';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function buildParams(filters: Partial<AttendanceFilterParams>): URLSearchParams {
  const p = new URLSearchParams();
  const entries: Array<[string, string | number | undefined]> = [
    ['employee_id',   filters.employee_id],
    ['department_id', filters.department_id],
    ['date',          filters.date],
    ['date_from',     filters.date_from],
    ['date_to',       filters.date_to],
    ['status',        filters.status],
    ['source',        filters.source],
    ['page',          filters.page],
    ['page_size',     filters.page_size],
  ];
  entries.forEach(([k, v]) => {
    if (v !== undefined && v !== '' && v !== null) p.set(k, String(v));
  });
  return p;
}

// ─── Shifts ───────────────────────────────────────────────────────────────────

export async function getShifts(): Promise<Shift[]> {
  const res = await api.get<Shift[]>('/api/v1/attendance/shifts');
  return res.data;
}

export async function createShift(data: ShiftCreate): Promise<Shift> {
  const res = await api.post<Shift>('/api/v1/attendance/shifts', data);
  return res.data;
}

export async function updateShift(id: string, data: Partial<ShiftCreate>): Promise<Shift> {
  const res = await api.patch<Shift>(`/api/v1/attendance/shifts/${id}`, data);
  return res.data;
}

// ─── Check-in / Check-out ─────────────────────────────────────────────────────

export async function checkIn(data: AttendanceCheckInRequest): Promise<AttendanceRecord> {
  const res = await api.post<AttendanceRecord>('/api/v1/attendance/check-in', data);
  return res.data;
}

export async function checkOut(data: AttendanceCheckOutRequest): Promise<AttendanceRecord> {
  const res = await api.post<AttendanceRecord>('/api/v1/attendance/check-out', data);
  return res.data;
}

export async function getTodayRecord(): Promise<AttendanceRecord | null> {
  const res = await api.get<AttendanceRecord | null>('/api/v1/attendance/today/me');
  return res.data;
}

// ─── Records ──────────────────────────────────────────────────────────────────

export async function getAttendanceRecords(
  filters: Partial<AttendanceFilterParams> = {},
): Promise<PaginatedAttendanceRecords> {
  const params = buildParams(filters);
  const res    = await api.get<PaginatedAttendanceRecords>(
    `/api/v1/attendance/records?${params.toString()}`,
  );
  return res.data;
}

export async function manualEntry(
  data: AttendanceManualEntryRequest,
): Promise<AttendanceRecord> {
  const res = await api.post<AttendanceRecord>('/api/v1/attendance/records', data);
  return res.data;
}

// ─── Adjustments ──────────────────────────────────────────────────────────────

export async function requestAdjustment(
  data: AttendanceAdjustmentRequest,
): Promise<AdjustmentRecord> {
  const res = await api.post<AdjustmentRecord>('/api/v1/attendance/adjustments', data);
  return res.data;
}

export async function getAdjustments(pending?: boolean): Promise<AdjustmentRecord[]> {
  const url = pending ? '/api/v1/attendance/adjustments?pending=true' : '/api/v1/attendance/adjustments';
  const res = await api.get<AdjustmentRecord[]>(url);
  return res.data;
}

export async function reviewAdjustment(
  id: string,
  action: 'approve' | 'reject',
  review_note?: string,
): Promise<AdjustmentRecord> {
  const res = await api.post<AdjustmentRecord>(
    `/api/v1/attendance/adjustments/${id}/${action}`,
    { action, review_note },
  );
  return res.data;
}

// ─── Summary & Timesheet ──────────────────────────────────────────────────────

export async function getAttendanceSummary(
  employeeId: string,
  month: number,
  year:  number,
): Promise<AttendanceSummary> {
  const res = await api.get<AttendanceSummary>(
    `/api/v1/attendance/summary/${employeeId}?month=${month}&year=${year}`,
  );
  return res.data;
}

export async function getTimesheet(
  employeeId: string,
  month: number,
  year:  number,
): Promise<TimesheetResponse> {
  const res = await api.get<TimesheetResponse>(
    `/api/v1/attendance/timesheet/${employeeId}?month=${month}&year=${year}`,
  );
  return res.data;
}

export async function exportTimesheet(
  employeeId: string,
  month: number,
  year:  number,
): Promise<Blob> {
  const res = await api.get(
    `/api/v1/attendance/timesheet/${employeeId}/export?month=${month}&year=${year}`,
    { responseType: 'blob' },
  );
  return res.data as Blob;
}

// ─── Live Dashboard ───────────────────────────────────────────────────────────

export async function getTodayAttendance(): Promise<LiveAttendanceEntry[]> {
  const res = await api.get<LiveAttendanceEntry[]>('/api/v1/attendance/today');
  return res.data;
}
