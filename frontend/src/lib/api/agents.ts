/**
 * Agent Factory — API client functions.
 * All calls go through the existing Axios instance (auth + tenant headers included).
 */

import { api } from '@/lib/api';

const BASE = '/api/v1/agent';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface OpenClawStatus {
  model:           string;
  api_key_set:     boolean;
  api_key_preview: string;
  max_tokens:      number;
  mode:            'live' | 'mock';
  hint:            string | null;
}

export interface AgentCapability {
  available: boolean;
  actions:   string[];
}

export interface AgentLog {
  id:                   string;
  task_id:              string;
  agent_name:           string;
  domain:               string;
  action:               string;
  status:               'success' | 'error' | 'skipped';
  result:               Record<string, unknown> | null;
  duration_ms:          number | null;
  tenant_id:            string | null;
  triggered_by:         string;
  triggered_by_user_id: string | null;
  model_used:           string | null;
  input_tokens:         number | null;
  output_tokens:        number | null;
  created_at:           string;
}

export interface AgentSystemStatus {
  timestamp:     string;
  system:        string;
  version:       string;
  openclaw:      OpenClawStatus;
  agents:        Record<string, AgentCapability>;
  beat_schedule: Record<string, { task: string; schedule: string }>;
  logs: {
    redis_count: number;
    db_stats:    Record<string, Record<string, number>>;
    recent:      AgentLog[];
  };
  routes:        Record<string, string>;
}

export interface AgentLogsResponse {
  total:  number;
  limit:  number;
  offset: number;
  logs:   AgentLog[];
}

export interface TriggerResponse {
  task_id:     string;
  domain:      string;
  action:      string;
  status:      string;
  result:      Record<string, unknown> | null;
  duration_ms: number | null;
  timestamp:   string;
}

export interface AgentLogsFilter {
  domain?:      string;
  status?:      string;
  triggered_by?: string;
  date_from?:   string;
  date_to?:     string;
  limit?:       number;
  offset?:      number;
}

// ─── Status ───────────────────────────────────────────────────────────────────

export async function fetchAgentStatus(): Promise<AgentSystemStatus> {
  const res = await api.get<AgentSystemStatus>(`${BASE}/status`);
  return res.data;
}

// ─── Logs ─────────────────────────────────────────────────────────────────────

export async function fetchAgentLogs(
  filter: AgentLogsFilter = {},
): Promise<AgentLogsResponse> {
  const params = new URLSearchParams();
  if (filter.domain)       params.set('domain',       filter.domain);
  if (filter.status)       params.set('status',       filter.status);
  if (filter.triggered_by) params.set('triggered_by', filter.triggered_by);
  if (filter.date_from)    params.set('date_from',    filter.date_from);
  if (filter.date_to)      params.set('date_to',      filter.date_to);
  params.set('limit',  String(filter.limit  ?? 25));
  params.set('offset', String(filter.offset ?? 0));

  const res = await api.get<AgentLogsResponse>(`${BASE}/logs?${params.toString()}`);
  return res.data;
}

// ─── Manual triggers ──────────────────────────────────────────────────────────

export async function triggerAttendanceReport(
  reportDate?: string,
): Promise<TriggerResponse> {
  const params = reportDate ? `?report_date=${reportDate}` : '';
  const res = await api.post<TriggerResponse>(
    `${BASE}/triggers/attendance/report${params}`,
  );
  return res.data;
}

export async function triggerLeaveAnomalies(
  lookbackDays = 90,
): Promise<TriggerResponse> {
  const res = await api.post<TriggerResponse>(
    `${BASE}/triggers/leave/detect-anomalies?lookback_days=${lookbackDays}`,
  );
  return res.data;
}

export async function triggerLeaveAnalysis(
  requestId: string,
): Promise<TriggerResponse> {
  const res = await api.post<TriggerResponse>(
    `${BASE}/triggers/leave/analyse/${requestId}`,
  );
  return res.data;
}

export async function triggerPayrollValidation(
  runId: string,
): Promise<TriggerResponse> {
  const res = await api.post<TriggerResponse>(
    `${BASE}/triggers/payroll/validate/${runId}`,
  );
  return res.data;
}

export async function triggerPayrollSummary(
  runId: string,
): Promise<TriggerResponse> {
  const res = await api.post<TriggerResponse>(
    `${BASE}/triggers/payroll/summarise/${runId}`,
  );
  return res.data;
}

export async function triggerChronicAbsentees(
  lookbackDays = 30,
  minAbsences  = 5,
): Promise<TriggerResponse> {
  const res = await api.get<TriggerResponse>(
    `${BASE}/triggers/attendance/absentees?lookback_days=${lookbackDays}&min_absences=${minAbsences}`,
  );
  return res.data;
}
