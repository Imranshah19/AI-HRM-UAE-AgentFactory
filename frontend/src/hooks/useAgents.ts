/**
 * Agent Factory — React Query hooks.
 * Wraps the agents API client with caching, auto-refresh, and mutation state.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import {
  fetchAgentStatus,
  fetchAgentLogs,
  triggerAttendanceReport,
  triggerLeaveAnomalies,
  triggerLeaveAnalysis,
  triggerPayrollValidation,
  triggerPayrollSummary,
  triggerChronicAbsentees,
  type AgentLogsFilter,
  type TriggerResponse,
} from '@/lib/api/agents';

// ─── Query keys ───────────────────────────────────────────────────────────────

export const AGENT_KEYS = {
  status:  ['agents', 'status']  as const,
  logs:    (filter: AgentLogsFilter) => ['agents', 'logs', filter] as const,
};

// ─── Status ───────────────────────────────────────────────────────────────────

/** Fetch full agent system status. Auto-refreshes every 30 seconds. */
export function useAgentStatus() {
  return useQuery({
    queryKey:        AGENT_KEYS.status,
    queryFn:         fetchAgentStatus,
    refetchInterval: 30_000,
    staleTime:       20_000,
    retry:           1,
  });
}

// ─── Logs ─────────────────────────────────────────────────────────────────────

/** Fetch paginated + filtered agent execution logs. Auto-refreshes every 30s. */
export function useAgentLogs(filter: AgentLogsFilter = {}) {
  return useQuery({
    queryKey:        AGENT_KEYS.logs(filter),
    queryFn:         () => fetchAgentLogs(filter),
    refetchInterval: 30_000,
    staleTime:       20_000,
    retry:           1,
  });
}

// ─── Trigger mutations ────────────────────────────────────────────────────────

function useTrigger(
  mutationFn: (...args: never[]) => Promise<TriggerResponse>,
  label:      string,
) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: mutationFn as () => Promise<TriggerResponse>,
    onSuccess: (data) => {
      const status = data.status === 'success' ? 'success' : 'info';
      const msg    = data.status === 'success'
        ? `${label} completed in ${data.duration_ms?.toFixed(0) ?? '?'}ms`
        : `${label} queued (task: ${data.task_id.slice(0, 8)}…)`;

      if (status === 'success') toast.success(msg);
      else                       toast.info(msg);

      // Invalidate logs so table refreshes
      void qc.invalidateQueries({ queryKey: ['agents', 'logs'] });
      void qc.invalidateQueries({ queryKey: AGENT_KEYS.status });
    },
    onError: (err: Error) => {
      toast.error(`${label} failed: ${err.message}`);
    },
  });
}

export function useTriggerAttendanceReport() {
  return useTrigger(
    triggerAttendanceReport as never,
    'Attendance Report',
  );
}

export function useTriggerLeaveAnomalies() {
  return useTrigger(
    triggerLeaveAnomalies as never,
    'Leave Anomaly Detection',
  );
}

export function useTriggerLeaveAnalysis() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (requestId: string) => triggerLeaveAnalysis(requestId),
    onSuccess: (data) => {
      const rec = (data.result as Record<string, string> | null)?.recommendation ?? 'review';
      toast.success(`Leave analysis complete: ${rec.toUpperCase()}`);
      void qc.invalidateQueries({ queryKey: ['agents', 'logs'] });
    },
    onError: (err: Error) => {
      toast.error(`Leave analysis failed: ${err.message}`);
    },
  });
}

export function useTriggerPayrollValidation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => triggerPayrollValidation(runId),
    onSuccess: (data) => {
      const rec   = (data.result as Record<string, unknown> | null)?.recommendation ?? 'review';
      const risk  = (data.result as Record<string, unknown> | null)?.total_risk_score ?? '?';
      toast.success(`Payroll validation: ${String(rec).toUpperCase()} (risk: ${String(risk)}/100)`);
      void qc.invalidateQueries({ queryKey: ['agents', 'logs'] });
    },
    onError: (err: Error) => {
      toast.error(`Payroll validation failed: ${err.message}`);
    },
  });
}

export function useTriggerPayrollSummary() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => triggerPayrollSummary(runId),
    onSuccess: () => {
      toast.success('Payroll summary generated');
      void qc.invalidateQueries({ queryKey: ['agents', 'logs'] });
    },
    onError: (err: Error) => {
      toast.error(`Summary failed: ${err.message}`);
    },
  });
}

export function useTriggerChronicAbsentees() {
  return useTrigger(
    triggerChronicAbsentees as never,
    'Chronic Absentee Report',
  );
}
