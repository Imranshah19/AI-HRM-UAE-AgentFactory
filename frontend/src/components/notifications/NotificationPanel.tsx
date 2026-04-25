'use client';

import { useRouter } from 'next/navigation';
import { formatDistanceToNow } from 'date-fns';
import {
  Bell, Check, CheckCheck, Info, AlertTriangle, AlertCircle,
  CheckCircle2, X,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Badge }  from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Popover, PopoverContent, PopoverTrigger,
} from '@/components/ui/popover';

import {
  useNotifications,
  useUnreadCount,
  useMarkRead,
  useMarkAllRead,
} from '@/hooks/useNotifications';
import { cn } from '@/lib/utils';
import type { Notification, NotificationType } from '@/types/notifications';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function typeIcon(type: NotificationType) {
  const cls = 'h-4 w-4 flex-shrink-0';
  switch (type) {
    case 'success': return <CheckCircle2  className={cn(cls, 'text-green-500')} />;
    case 'warning': return <AlertTriangle className={cn(cls, 'text-amber-500')} />;
    case 'error':   return <AlertCircle  className={cn(cls, 'text-red-500')}   />;
    default:        return <Info          className={cn(cls, 'text-blue-500')}  />;
  }
}

function timeAgo(dateStr: string): string {
  try {
    return formatDistanceToNow(new Date(dateStr), { addSuffix: true });
  } catch {
    return '';
  }
}

// ─── Single notification row ──────────────────────────────────────────────────

function NotificationRow({
  notif,
  onMarkRead,
}: {
  notif:      Notification;
  onMarkRead: (id: string) => void;
}) {
  const router = useRouter();

  function handleClick() {
    if (!notif.is_read) onMarkRead(notif.id);
    if (notif.action_url) router.push(notif.action_url);
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(e) => e.key === 'Enter' && handleClick()}
      className={cn(
        'flex gap-3 px-4 py-3 cursor-pointer transition-colors border-b border-slate-100 last:border-0',
        notif.is_read
          ? 'hover:bg-slate-50'
          : 'bg-blue-50/60 hover:bg-blue-50',
      )}
    >
      <div className="pt-0.5">{typeIcon(notif.type)}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p className={cn(
            'text-sm leading-snug truncate',
            notif.is_read ? 'text-slate-600' : 'text-slate-800 font-medium',
          )}>
            {notif.title}
          </p>
          {!notif.is_read && (
            <span className="flex-shrink-0 w-2 h-2 rounded-full bg-blue-500 mt-1" />
          )}
        </div>
        <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{notif.message}</p>
        <p className="text-xs text-slate-400 mt-1">{timeAgo(notif.created_at)}</p>
      </div>
    </div>
  );
}

// ─── Panel ────────────────────────────────────────────────────────────────────

export function NotificationPanel() {
  const router = useRouter();
  const { data, isLoading }   = useNotifications();
  const { data: unreadCount } = useUnreadCount();
  const markRead    = useMarkRead();
  const markAllRead = useMarkAllRead();

  const notifications = data?.notifications ?? [];
  const count         = unreadCount ?? data?.unread_count ?? 0;

  function handleMarkRead(id: string) {
    markRead.mutate({ notification_ids: [id] });
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative text-slate-500 hover:text-slate-700"
          aria-label={`Notifications${count > 0 ? ` (${count} unread)` : ''}`}
        >
          <Bell className="h-4 w-4" />
          {count > 0 && (
            <Badge
              className="absolute -top-0.5 -right-0.5 h-4 min-w-[1rem] px-0.5 text-[10px] bg-red-500 text-white border-white border"
            >
              {count > 99 ? '99+' : count}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent
        align="end"
        className="w-96 p-0 shadow-lg"
        sideOffset={8}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Bell className="h-4 w-4 text-slate-500" />
            <span className="font-semibold text-sm text-slate-800">Notifications</span>
            {count > 0 && (
              <Badge className="bg-blue-100 text-blue-700 text-xs px-1.5 py-0">
                {count} new
              </Badge>
            )}
          </div>
          {count > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="text-xs text-slate-500 hover:text-slate-700 h-7 px-2"
              onClick={() => markAllRead.mutate()}
              disabled={markAllRead.isPending}
            >
              <CheckCheck className="h-3.5 w-3.5 mr-1" />
              Mark all read
            </Button>
          )}
        </div>

        {/* List */}
        <ScrollArea className="max-h-96">
          {isLoading ? (
            <div className="py-8 text-center text-slate-400 text-sm">Loading…</div>
          ) : notifications.length === 0 ? (
            <div className="py-10 text-center">
              <Bell className="h-8 w-8 mx-auto mb-2 text-slate-200" />
              <p className="text-sm text-slate-400">No notifications yet</p>
            </div>
          ) : (
            notifications.slice(0, 20).map((n) => (
              <NotificationRow key={n.id} notif={n} onMarkRead={handleMarkRead} />
            ))
          )}
        </ScrollArea>

        {/* Footer */}
        {notifications.length > 0 && (
          <div className="border-t border-slate-100 px-4 py-2">
            <Button
              variant="ghost"
              size="sm"
              className="w-full text-xs text-slate-500 hover:text-slate-700"
              onClick={() => router.push('/notifications')}
            >
              View all notifications
            </Button>
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
}
