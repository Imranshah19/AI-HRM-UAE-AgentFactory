'use client';

/**
 * AI-HRMS — AI feature TanStack Query hooks.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as aiApi from '@/lib/api/ai';
import { extractApiError } from '@/lib/auth';

export const aiKeys = {
  attritionOverview:        () => ['ai', 'attrition', 'overview'] as const,
  attritionEmployee:        (id: string) => ['ai', 'attrition', id] as const,
  performanceEmployee:      (id: string) => ['ai', 'performance', id] as const,
  performanceTeam:          (id: string) => ['ai', 'performance', 'team', id] as const,
  anomalies:                () => ['ai', 'anomalies'] as const,
  insights:                 () => ['ai', 'insights'] as const,
  chatSuggestions:          () => ['ai', 'chat', 'suggestions'] as const,
};

// ─── Attrition ────────────────────────────────────────────────────────────────

export function useAttritionOverview() {
  return useQuery({
    queryKey: aiKeys.attritionOverview(),
    queryFn:  () => aiApi.getAttritionOverview(),
    staleTime: 5 * 60 * 1000,   // 5 min — server caches 6h
    retry: 1,
  });
}

export function useAttritionRisk(employeeId?: string) {
  return useQuery({
    queryKey: aiKeys.attritionEmployee(employeeId ?? ''),
    queryFn:  () => aiApi.getEmployeeAttrition(employeeId!),
    enabled:  !!employeeId,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}

export function useBulkAttrition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => aiApi.triggerBulkAttrition(),
    onSuccess: (data) => {
      toast.success(data.message);
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: aiKeys.attritionOverview() });
      }, 35_000);
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}

// ─── Performance ──────────────────────────────────────────────────────────────

export function usePerformancePrediction(employeeId?: string) {
  return useQuery({
    queryKey: aiKeys.performanceEmployee(employeeId ?? ''),
    queryFn:  () => aiApi.getPerformancePrediction(employeeId!),
    enabled:  !!employeeId,
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });
}

export function useTeamPerformancePredictions(managerId?: string) {
  return useQuery({
    queryKey: aiKeys.performanceTeam(managerId ?? ''),
    queryFn:  () => aiApi.getTeamPerformancePredictions(managerId!),
    enabled:  !!managerId,
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });
}

// ─── Analytics ────────────────────────────────────────────────────────────────

export function useAnomalies() {
  return useQuery({
    queryKey:        aiKeys.anomalies(),
    queryFn:         () => aiApi.getAnomalies(),
    staleTime:       5 * 60 * 1000,
    refetchInterval: 10 * 60 * 1000,   // re-check every 10 min
    retry: 1,
  });
}

export function useAIInsights() {
  return useQuery({
    queryKey:        aiKeys.insights(),
    queryFn:         () => aiApi.getAIInsights(),
    staleTime:       5 * 60 * 1000,
    refetchInterval: 10 * 60 * 1000,
    retry: 1,
  });
}

// ─── Chatbot ──────────────────────────────────────────────────────────────────

export function useChatbot() {
  return useMutation({
    mutationFn: ({
      message,
      history,
    }: {
      message: string;
      history?: Array<{ role: string; content: string }>;
    }) => aiApi.sendChatMessage(message, history),
    onError: (err) => toast.error(extractApiError(err)),
  });
}

export function useChatSuggestions() {
  return useQuery({
    queryKey: aiKeys.chatSuggestions(),
    queryFn:  () => aiApi.getChatSuggestions(),
    staleTime: 60 * 60 * 1000,   // suggestions rarely change
  });
}
