'use client';

export const dynamic = 'force-dynamic';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import { useAuthStore } from '@/stores/authStore';
import { getMyProfile } from '@/lib/auth';
import { Sidebar }     from '@/components/layout/Sidebar';
import { TopNavbar }   from '@/components/layout/TopNavbar';
import { Skeleton }    from '@/components/ui/skeleton';

/**
 * Dashboard group layout.
 *
 * On mount:
 *   1. If the Zustand store already has a user → render immediately.
 *   2. If not → call GET /auth/me to re-hydrate the session.
 *   3. If the request fails (401) → the Axios interceptor redirects to /login.
 *
 * Structure:
 *   ┌──────────────────────────────────────┐
 *   │  Sidebar  │  TopNavbar               │
 *   │  (fixed)  ├──────────────────────────│
 *   │           │  <children>              │
 *   └──────────────────────────────────────┘
 */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router            = useRouter();
  const { user, setUser, isAuthenticated } = useAuthStore();
  const [checking,        setChecking]     = useState(!isAuthenticated);
  const [mobileNavOpen,   setMobileNavOpen] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      setChecking(false);
      return;
    }

    let cancelled = false;

    async function verify() {
      try {
        const profile = await getMyProfile();
        if (!cancelled) {
          setUser(profile);
          setChecking(false);
        }
      } catch {
        // 401 → Axios interceptor already redirects to /login
        if (!cancelled) router.replace('/login');
      }
    }

    verify();
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Loading skeleton ──────────────────────────────────────────────────────
  if (checking) {
    return (
      <div className="flex h-screen bg-slate-50 dark:bg-slate-950">
        {/* Sidebar skeleton */}
        <div className="hidden lg:flex flex-col w-64 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 gap-4">
          <Skeleton className="h-8 w-32" />
          <div className="space-y-2 mt-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-9 w-full rounded-lg" />
            ))}
          </div>
        </div>
        {/* Main skeleton */}
        <div className="flex-1 flex flex-col">
          <div className="h-16 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-6 flex items-center gap-4">
            <Skeleton className="h-5 w-40" />
            <div className="ml-auto flex gap-2">
              <Skeleton className="h-8 w-8 rounded-md" />
              <Skeleton className="h-8 w-8 rounded-md" />
              <Skeleton className="h-8 w-24 rounded-lg" />
            </div>
          </div>
          <main className="flex-1 p-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-28 rounded-xl" />
              ))}
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Skeleton className="h-64 rounded-xl" />
              <Skeleton className="h-64 rounded-xl" />
            </div>
          </main>
        </div>
      </div>
    );
  }

  // ── Authenticated layout ──────────────────────────────────────────────────
  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 dark:bg-slate-950">
      {/* Sidebar */}
      <Sidebar
        mobileOpen={mobileNavOpen}
        onMobileClose={() => setMobileNavOpen(false)}
      />

      {/* Main column */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <TopNavbar onMenuClick={() => setMobileNavOpen(true)} />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
