/**
 * AI-HRMS — AI feature API calls.
 */

import { api } from '@/lib/api';
import type {
  AIInsights,
  Anomaly,
  AttritionOverview,
  AttritionResult,
  ChatResponse,
  ChatSuggestionsResponse,
  PerformancePrediction,
} from '@/types/ai';

// ─── Attrition ────────────────────────────────────────────────────────────────

export async function getAttritionOverview(): Promise<AttritionOverview> {
  const res = await api.get<AttritionOverview>('/api/v1/ai/attrition/overview');
  return res.data;
}

export async function getEmployeeAttrition(
  employeeId: string,
  force = false,
): Promise<AttritionResult> {
  const res = await api.get<AttritionResult>(
    `/api/v1/ai/attrition/${employeeId}${force ? '?force=true' : ''}`,
  );
  return res.data;
}

export async function triggerBulkAttrition(): Promise<{ message: string }> {
  const res = await api.post<{ message: string }>('/api/v1/ai/attrition/bulk-predict');
  return res.data;
}

// ─── Performance ──────────────────────────────────────────────────────────────

export async function getPerformancePrediction(
  employeeId: string,
): Promise<PerformancePrediction> {
  const res = await api.get<PerformancePrediction>(
    `/api/v1/ai/performance/${employeeId}`,
  );
  return res.data;
}

export async function getTeamPerformancePredictions(
  managerId: string,
): Promise<PerformancePrediction[]> {
  const res = await api.get<PerformancePrediction[]>(
    `/api/v1/ai/performance/team/${managerId}`,
  );
  return res.data;
}

// ─── Analytics ────────────────────────────────────────────────────────────────

export async function getAnomalies(): Promise<Anomaly[]> {
  const res = await api.get<Anomaly[]>('/api/v1/ai/analytics/anomalies');
  return res.data;
}

export async function getAIInsights(): Promise<AIInsights> {
  const res = await api.get<AIInsights>('/api/v1/ai/analytics/insights');
  return res.data;
}

// ─── Chatbot ──────────────────────────────────────────────────────────────────

export async function sendChatMessage(
  message: string,
  history: Array<{ role: string; content: string }> = [],
): Promise<ChatResponse> {
  const res = await api.post<ChatResponse>('/api/v1/ai/chat/', {
    message,
    conversation_history: history,
  });
  return res.data;
}

export async function getChatSuggestions(): Promise<ChatSuggestionsResponse> {
  const res = await api.get<ChatSuggestionsResponse>('/api/v1/ai/chat/suggestions');
  return res.data;
}
