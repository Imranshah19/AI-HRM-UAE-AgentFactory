'use client';

export const dynamic = 'force-dynamic';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';

/**
 * Auth group layout — /login, /forgot-password, /change-password
 *
 * If the user is already authenticated (e.g. revisits /login),
 * redirect them straight to the dashboard.
 * Otherwise render a clean, full-height page with no chrome.
 *
 * The `mounted` guard prevents a blank-page flash: on the server (SSR) and
 * during the first client render, `mounted` is false so we always render
 * children — matching the server HTML exactly and avoiding hydration errors.
 * Only AFTER mount do we act on Zustand's rehydrated auth state.
 */
export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (mounted && isAuthenticated) {
      router.replace('/dashboard');
    }
  }, [mounted, isAuthenticated, router]);

  // Always render children — let the redirect happen in the background.
  // Never return null, which causes the blank white flash.
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      {children}
    </div>
  );
}
