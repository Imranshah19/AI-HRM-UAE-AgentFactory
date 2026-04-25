'use client';

/**
 * AI-HRMS — Attendance module TanStack Query hooks + WebSocket.
 *
 * Query keys:
 *   ['shifts']
 *   ['today-attendance']                  → current user's today record
 *   ['attendance-records', filters]
 *   ['attendance-summary', empId, m, y]
 *   ['attendance-timesheet', empId, m, y]
 *   ['today-live']                        → HR live dashboard
 *   ['adjustments', scope]
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient }     from '@tanstack/react-query';
import { toast }       from 'sonner';

import * as attendanceApi from '@/lib/api/attendance';
import { extractApiError } from '@/lib/auth';
import { useAuthStore }    from '@/stores/authStore';
import type {
  AttendanceCheckInRequest,
  AttendanceCheckOutRequest,
  AttendanceFilterParams,
  AttendanceManualEntryRequest,
  AttendanceAdjustmentRequest,
  LiveAttendanceEntry,
} from '@/types/attendance';

// ─── Query keys ───────────────────────────────────────────────────────────────

export const attKeys = {
  shifts:     ()                                   => ['shifts'] as const,
  today:      ()                                   => ['today-attendance'] as const,
  records:    (f: Partial<AttendanceFilterParams>) => ['attendance-records', f] as const,
  summary:    (id: string, m: number, y: number)   => ['attendance-summary', id, m, y] as const,
  timesheet:  (id: string, m: number, y: number)   => ['attendance-timesheet', id, m, y] as const,
  live:       ()                                   => ['today-live'] as const,
  adjustments:(scope: string)                      => ['adjustments', scope] as const,
};

// ─── Shifts ───────────────────────────────────────────────────────────────────

export function useShifts() {
  return useQuery({
    queryKey:  attKeys.shifts(),
    queryFn:   attendanceApi.getShifts,
    staleTime: 300_000,
  });
}

// ─── Today's record ───────────────────────────────────────────────────────────

export function useTodayAttendance() {
  return useQuery({
    queryKey:  attKeys.today(),
    queryFn:   attendanceApi.getTodayRecord,
    staleTime: 30_000,
    refetchInterval: 60_000,   // refresh every minute
  });
}

// ─── Check-in / Check-out ─────────────────────────────────────────────────────

export function useCheckIn() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AttendanceCheckInRequest) => attendanceApi.checkIn(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: attKeys.today() });
      qc.invalidateQueries({ queryKey: attKeys.live() });
      qc.invalidateQueries({ queryKey: ['attendance-records'] });
      toast.success('Checked in successfully.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

export function useCheckOut() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AttendanceCheckOutRequest) => attendanceApi.checkOut(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: attKeys.today() });
      qc.invalidateQueries({ queryKey: attKeys.live() });
      qc.invalidateQueries({ queryKey: ['attendance-records'] });
      toast.success('Checked out successfully.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

// ─── Records ──────────────────────────────────────────────────────────────────

export function useAttendanceRecords(filters: Partial<AttendanceFilterParams> = {}) {
  return useQuery({
    queryKey:        attKeys.records(filters),
    queryFn:         () => attendanceApi.getAttendanceRecords(filters),
    staleTime:       30_000,
    placeholderData: (prev) => prev,
  });
}

export function useManualEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AttendanceManualEntryRequest) => attendanceApi.manualEntry(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['attendance-records'] });
      toast.success('Attendance record created.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

// ─── Summary & Timesheet ──────────────────────────────────────────────────────

export function useAttendanceSummary(
  employeeId: string | undefined,
  month: number,
  year:  number,
) {
  return useQuery({
    queryKey:  attKeys.summary(employeeId ?? '', month, year),
    queryFn:   () => attendanceApi.getAttendanceSummary(employeeId!, month, year),
    staleTime: 120_000,
    enabled:   !!employeeId,
  });
}

export function useTimesheet(
  employeeId: string | undefined,
  month: number,
  year:  number,
) {
  return useQuery({
    queryKey:  attKeys.timesheet(employeeId ?? '', month, year),
    queryFn:   () => attendanceApi.getTimesheet(employeeId!, month, year),
    staleTime: 60_000,
    enabled:   !!employeeId,
  });
}

export function useExportTimesheet() {
  return useCallback(async (employeeId: string, month: number, year: number) => {
    try {
      const blob = await attendanceApi.exportTimesheet(employeeId, month, year);
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = `timesheet_${year}_${String(month).padStart(2, '0')}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(extractApiError(e));
    }
  }, []);
}

// ─── Adjustments ──────────────────────────────────────────────────────────────

export function useAdjustments(scope: 'mine' | 'pending' = 'mine') {
  return useQuery({
    queryKey: attKeys.adjustments(scope),
    queryFn:  () => attendanceApi.getAdjustments(scope === 'pending'),
    staleTime: 30_000,
  });
}

export function useRequestAdjustment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AttendanceAdjustmentRequest) => attendanceApi.requestAdjustment(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['adjustments'] });
      toast.success('Adjustment request submitted.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

export function useReviewAdjustment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action, note }: { id: string; action: 'approve' | 'reject'; note?: string }) =>
      attendanceApi.reviewAdjustment(id, action, note),
    onSuccess: (_, { action }) => {
      qc.invalidateQueries({ queryKey: ['adjustments'] });
      qc.invalidateQueries({ queryKey: ['attendance-records'] });
      toast.success(action === 'approve' ? 'Adjustment approved.' : 'Adjustment rejected.');
    },
    onError: (e: unknown) => toast.error(extractApiError(e)),
  });
}

// ─── Live Today (HR dashboard, HTTP poll) ─────────────────────────────────────

export function useLiveTodayList() {
  return useQuery({
    queryKey:        attKeys.live(),
    queryFn:         attendanceApi.getTodayAttendance,
    staleTime:       10_000,
    refetchInterval: 30_000,
  });
}

// ─── Live Attendance — WebSocket hook ─────────────────────────────────────────

const MAX_FEED = 50;
const BACKOFF  = [1_000, 2_000, 5_000, 10_000, 30_000];

export function useLiveAttendance() {
  const [feed,      setFeed]      = useState<LiveAttendanceEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef    = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountRef = useRef(true);

  const tenantSlug = useAuthStore.getState().tenantSlug;

  const connect = useCallback(() => {
    if (!mountRef.current) return;

    // Derive WS URL from current page origin
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const base      = `${protocol}://${window.location.host}`;

    // Get JWT from store for auth
    const user  = useAuthStore.getState().user;
    // We pass a lightweight identifier; the backend validates via cookie or query param
    const token = (user as any)?._token ?? '';

    const url = `${base}/api/v1/attendance/live?token=${encodeURIComponent(token)}&tenant=${tenantSlug}`;
    const ws  = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      retryRef.current = 0;
    };

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data) as LiveAttendanceEntry & { type?: string };
        if (msg.type !== 'attendance') return;
        const entry: LiveAttendanceEntry = { ...msg, _key: `${msg.employee_id}-${Date.now()}` };
        setFeed((prev) => [entry, ...prev].slice(0, MAX_FEED));
      } catch {
        // ignore malformed
      }
    };

    ws.onclose = () => {
      setConnected(false);
      if (!mountRef.current) return;
      const delay = BACKOFF[Math.min(retryRef.current, BACKOFF.length - 1)];
      retryRef.current++;
      timerRef.current = setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [tenantSlug]);

  useEffect(() => {
    mountRef.current = true;
    connect();
    return () => {
      mountRef.current = false;
      if (timerRef.current) clearTimeout(timerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { feed, connected };
}
