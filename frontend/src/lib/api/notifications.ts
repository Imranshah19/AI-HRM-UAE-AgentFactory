/**
 * AI-HRMS — Notifications API calls.
 */

import { api } from '@/lib/api';
import type {
  MarkReadRequest,
  Notification,
  NotificationListResponse,
} from '@/types/notifications';

export async function getNotifications(): Promise<NotificationListResponse> {
  const res = await api.get<NotificationListResponse>('/api/v1/notifications');
  return res.data;
}

export async function getUnreadCount(): Promise<number> {
  const res = await api.get<{ unread_count: number }>('/api/v1/notifications/unread-count');
  return res.data.unread_count;
}

export async function markRead(data: MarkReadRequest): Promise<{ updated: number }> {
  const res = await api.post<{ updated: number }>('/api/v1/notifications/mark-read', data);
  return res.data;
}

export async function markAllRead(): Promise<{ updated: number }> {
  const res = await api.post<{ updated: number }>('/api/v1/notifications/mark-all-read', {});
  return res.data;
}
