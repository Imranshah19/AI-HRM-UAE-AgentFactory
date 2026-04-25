'use client';

/**
 * AI-HRMS — Notifications TanStack Query hooks.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as notifApi       from '@/lib/api/notifications';
import { extractApiError } from '@/lib/auth';
import type { MarkReadRequest } from '@/types/notifications';

export const notificationKeys = {
  list:        () => ['notifications'] as const,
  unreadCount: () => ['notifications-unread-count'] as const,
};

export function useNotifications() {
  return useQuery({
    queryKey:       notificationKeys.list(),
    queryFn:        () => notifApi.getNotifications(),
    staleTime:      15_000,
    refetchInterval: 30_000,   // auto-refresh every 30s
  });
}

export function useUnreadCount() {
  return useQuery({
    queryKey:       notificationKeys.unreadCount(),
    queryFn:        () => notifApi.getUnreadCount(),
    staleTime:      15_000,
    refetchInterval: 30_000,
  });
}

export function useMarkRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: MarkReadRequest) => notifApi.markRead(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: notificationKeys.list() });
      qc.invalidateQueries({ queryKey: notificationKeys.unreadCount() });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}

export function useMarkAllRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => notifApi.markAllRead(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: notificationKeys.list() });
      qc.invalidateQueries({ queryKey: notificationKeys.unreadCount() });
      toast.success('All notifications marked as read');
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}
