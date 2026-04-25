'use client';

import { useEffect, useRef } from 'react';
import { format }            from 'date-fns';
import { Wifi, WifiOff }     from 'lucide-react';
import { EmployeeAvatar }    from '@/components/employees/EmployeeAvatar';
import { cn }                from '@/lib/utils';
import type { LiveAttendanceEntry } from '@/types/attendance';

// ─── Single feed entry ────────────────────────────────────────────────────────

function FeedEntry({ entry, isNew }: { entry: LiveAttendanceEntry; isNew: boolean }) {
  const isCheckIn = entry.action === 'check_in';
  const time      = new Date(entry.time);

  return (
    <div
      className={cn(
        'flex items-center gap-3 px-4 py-3 border-b last:border-0',
        'dark:border-slate-800 transition-all',
        isNew && 'animate-slide-in bg-hrms-50/40 dark:bg-hrms-950/10',
      )}
    >
      {/* Avatar */}
      <div className="relative shrink-0">
        <EmployeeAvatar
          name={entry.employee_name}
          photoUrl={entry.photo_url}
          size="sm"
        />
        {/* Action badge */}
        <span
          className={cn(
            'absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full border-2 border-white dark:border-slate-900',
            'flex items-center justify-center text-[8px] font-bold',
            isCheckIn
              ? 'bg-green-500 text-white'
              : 'bg-orange-500 text-white',
          )}
        >
          {isCheckIn ? '↑' : '↓'}
        </span>
      </div>

      {/* Details */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-800 dark:text-slate-100 truncate">
          {entry.employee_name}
        </p>
        <p className="text-xs text-slate-500 truncate">
          {entry.department_name ?? ''}
          {entry.department_name && ' · '}
          <span className={isCheckIn ? 'text-green-600' : 'text-orange-500'}>
            {isCheckIn ? 'Checked in' : 'Checked out'}
          </span>
        </p>
      </div>

      {/* Time */}
      <span className="text-xs text-slate-400 shrink-0 tabular-nums">
        {format(time, 'HH:mm')}
      </span>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

interface LiveFeedProps {
  feed:       LiveAttendanceEntry[];
  connected:  boolean;
  className?: string;
}

export function LiveFeed({ feed, connected, className }: LiveFeedProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevLen   = useRef(0);

  // Auto-scroll to top when new entries arrive
  useEffect(() => {
    if (feed.length > prevLen.current && scrollRef.current) {
      scrollRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
    prevLen.current = feed.length;
  }, [feed.length]);

  return (
    <div className={cn('flex flex-col rounded-xl border bg-white dark:bg-slate-900 overflow-hidden', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
          Live Attendance Feed
        </h3>
        <div className="flex items-center gap-1.5 text-xs">
          {connected ? (
            <>
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-green-600 dark:text-green-400">Live</span>
            </>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-red-500" />
              <span className="text-red-500">Reconnecting…</span>
            </>
          )}
        </div>
      </div>

      {/* Feed list */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto max-h-[420px]"
      >
        {feed.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-slate-400">
            <div className="text-3xl mb-2">📡</div>
            <p className="text-sm">Waiting for check-ins…</p>
            {!connected && (
              <p className="text-xs mt-1 text-red-400">
                Connection lost — attempting to reconnect
              </p>
            )}
          </div>
        ) : (
          feed.map((entry, idx) => (
            <FeedEntry
              key={entry._key ?? `${entry.employee_id}-${idx}`}
              entry={entry}
              isNew={idx === 0}
            />
          ))
        )}
      </div>

      {/* Footer count */}
      {feed.length > 0 && (
        <div className="px-4 py-2 border-t dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/30">
          <p className="text-xs text-slate-400 text-center">
            {feed.length} event{feed.length !== 1 ? 's' : ''} today
          </p>
        </div>
      )}

      {/* Slide-in animation */}
      <style>{`
        @keyframes slideIn {
          from { opacity: 0; transform: translateY(-8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .animate-slide-in {
          animation: slideIn 0.3s ease-out forwards;
        }
      `}</style>
    </div>
  );
}
