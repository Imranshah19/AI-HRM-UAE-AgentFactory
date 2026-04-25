'use client';

import { useEffect, useState, useCallback } from 'react';
import { MapPin, Clock, Zap } from 'lucide-react';
import { Button }   from '@/components/ui/button';
import { cn }       from '@/lib/utils';
import type { AttendanceRecord, Shift } from '@/types/attendance';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function pad(n: number): string {
  return String(n).padStart(2, '0');
}

function formatDuration(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  return `${pad(h)}:${pad(m)}:${pad(s)}`;
}

function formatTime(dt: string): string {
  return new Date(dt).toLocaleTimeString('en-US', {
    hour:   '2-digit',
    minute: '2-digit',
    hour12: true,
  });
}

// ─── Live clock ───────────────────────────────────────────────────────────────

function LiveClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="text-center">
      <p className="text-5xl font-bold tabular-nums text-slate-800 dark:text-slate-100 tracking-tight">
        {now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
      </p>
      <p className="text-sm text-slate-400 mt-1">
        {now.toLocaleDateString('en-PK', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
      </p>
    </div>
  );
}

// ─── Working hours counter ────────────────────────────────────────────────────

function WorkingHoursCounter({ checkInTime }: { checkInTime: string }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const start = new Date(checkInTime).getTime();
    const tick  = () => setElapsed(Date.now() - start);
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [checkInTime]);

  return (
    <div className="text-center">
      <p className="text-xs text-slate-500 mb-0.5">Working time</p>
      <p className="text-2xl font-bold tabular-nums text-hrms-600 dark:text-hrms-400">
        {formatDuration(elapsed)}
      </p>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

interface CheckInCardProps {
  todayRecord?:   AttendanceRecord | null;
  shift?:         Shift | null;
  onCheckIn:      (geo?: { lat: number; lng: number; address?: string }) => Promise<void>;
  onCheckOut:     () => Promise<void>;
  isPending?:     boolean;
}

export function CheckInCard({
  todayRecord,
  shift,
  onCheckIn,
  onCheckOut,
  isPending = false,
}: CheckInCardProps) {
  const [geoLoading, setGeoLoading] = useState(false);
  const [geoError,   setGeoError]   = useState<string | null>(null);

  const isCheckedIn  = !!todayRecord?.check_in && !todayRecord?.check_out;
  const isCheckedOut = !!todayRecord?.check_out;

  const handleCheckInGeo = useCallback(async () => {
    if (!navigator.geolocation) {
      await onCheckIn();
      return;
    }
    setGeoLoading(true);
    setGeoError(null);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        setGeoLoading(false);
        await onCheckIn({
          lat:     pos.coords.latitude,
          lng:     pos.coords.longitude,
          address: undefined,
        });
      },
      async (err) => {
        setGeoLoading(false);
        setGeoError(`Location unavailable: ${err.message}`);
        await onCheckIn();   // fall back to check-in without geo
      },
      { timeout: 8000, maximumAge: 60_000 },
    );
  }, [onCheckIn]);

  return (
    <div className="rounded-2xl border bg-white dark:bg-slate-900 shadow-sm overflow-hidden">
      {/* Animated header bar */}
      <div className={cn(
        'h-1.5 w-full transition-colors duration-700',
        isCheckedIn  ? 'bg-green-500' :
        isCheckedOut ? 'bg-blue-500'  :
        'bg-slate-200 dark:bg-slate-700',
      )} />

      <div className="p-6 space-y-6">
        {/* Clock */}
        <LiveClock />

        {/* Status indicator */}
        <div className="flex items-center justify-center gap-2">
          <span className={cn(
            'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium border',
            isCheckedIn  ? 'bg-green-50 border-green-300 text-green-700 dark:bg-green-950/30 dark:text-green-400' :
            isCheckedOut ? 'bg-blue-50  border-blue-300  text-blue-700  dark:bg-blue-950/30  dark:text-blue-400'  :
            'bg-slate-50 border-slate-200 text-slate-500',
          )}>
            <span className={cn(
              'w-2 h-2 rounded-full',
              isCheckedIn ? 'bg-green-500 animate-pulse' :
              isCheckedOut ? 'bg-blue-500' :
              'bg-slate-300',
            )} />
            {isCheckedIn  ? `Checked in at ${formatTime(todayRecord!.check_in!)}` :
             isCheckedOut ? `Checked out at ${formatTime(todayRecord!.check_out!)}` :
             'Not checked in'}
          </span>
        </div>

        {/* Working hours counter */}
        {isCheckedIn && todayRecord?.check_in && (
          <WorkingHoursCounter checkInTime={todayRecord.check_in} />
        )}

        {/* Completed working hours */}
        {isCheckedOut && todayRecord?.working_hours && (
          <div className="text-center">
            <p className="text-xs text-slate-500 mb-0.5">Total worked</p>
            <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {todayRecord.working_hours.toFixed(1)}h
              {(todayRecord.overtime_hours ?? 0) > 0 && (
                <span className="text-sm text-orange-500 ml-2">
                  +{todayRecord.overtime_hours?.toFixed(1)}h OT
                </span>
              )}
            </p>
          </div>
        )}

        {/* Shift info */}
        {shift && (
          <div className="flex items-center justify-center gap-2 text-xs text-slate-400">
            <Clock className="h-3.5 w-3.5" />
            Shift: {shift.start_time.slice(0, 5)} – {shift.end_time.slice(0, 5)}
            <span className="text-slate-300">·</span>
            Grace: {shift.grace_period_minutes}m
          </div>
        )}

        {/* Action buttons */}
        {!isCheckedOut && (
          <div className="space-y-2">
            {!isCheckedIn ? (
              <>
                <Button
                  size="lg"
                  className="w-full bg-green-600 hover:bg-green-700 text-white text-base font-semibold h-14 rounded-xl shadow-md shadow-green-100 dark:shadow-none"
                  onClick={() => onCheckIn()}
                  disabled={isPending || geoLoading}
                >
                  {isPending ? 'Checking in…' : '✓ Check In'}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full gap-2 text-slate-500"
                  onClick={handleCheckInGeo}
                  disabled={isPending || geoLoading}
                >
                  <MapPin className="h-3.5 w-3.5" />
                  {geoLoading ? 'Getting location…' : 'Check in with location'}
                </Button>
                {geoError && (
                  <p className="text-xs text-red-500 text-center">{geoError}</p>
                )}
              </>
            ) : (
              <Button
                size="lg"
                variant="destructive"
                className="w-full text-base font-semibold h-14 rounded-xl"
                onClick={onCheckOut}
                disabled={isPending}
              >
                {isPending ? 'Checking out…' : '✗ Check Out'}
              </Button>
            )}
          </div>
        )}

        {/* Location display */}
        {todayRecord?.location_address && (
          <div className="flex items-center gap-2 text-xs text-slate-400 justify-center">
            <MapPin className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">{todayRecord.location_address}</span>
          </div>
        )}
      </div>
    </div>
  );
}
