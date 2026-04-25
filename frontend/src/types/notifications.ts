// AI-HRMS — Notification TypeScript types

export type NotificationType    = 'info' | 'success' | 'warning' | 'error';
export type NotificationCategory =
  | 'leave' | 'attendance' | 'payroll' | 'performance' | 'recruitment'
  | 'training' | 'asset' | 'onboarding' | 'offboarding' | 'compliance'
  | 'system' | 'general';

export interface Notification {
  id:           string;
  title:        string;
  message:      string;
  type:         NotificationType;
  category:     NotificationCategory;
  action_url:   string | null;
  action_label: string | null;
  is_read:      boolean;
  read_at:      string | null;
  created_at:   string;
}

export interface NotificationListResponse {
  notifications: Notification[];
  unread_count:  number;
}

export interface MarkReadRequest {
  notification_ids: string[];
}
