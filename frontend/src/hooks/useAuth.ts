'use client';

import { useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';
import { getMyProfile, logoutUser } from '@/lib/auth';

/**
 * useAuth — primary authentication hook.
 *
 * On mount (when the store is empty / after a hard refresh):
 *   - calls GET /auth/me to re-hydrate the user from the active session cookie
 *   - sets isLoading while the request is in flight
 *
 * Returns:
 *   user            — the authenticated User object or null
 *   isAuthenticated — true when user is set
 *   isLoading       — true during the initial profile fetch
 *   hasPermission   — checks module.action in the user's permissions
 *   hasRole         — checks a role name in the user's roles
 *   logout          — calls logoutUser() then redirects to /login
 */
export function useAuth() {
  const router = useRouter();
  const {
    user,
    isAuthenticated,
    isLoading,
    setUser,
    clearUser,
    setLoading,
    hasPermission,
    hasRole,
  } = useAuthStore();

  // ── Re-hydrate profile on mount if store is empty ─────────────────────────
  useEffect(() => {
    if (isAuthenticated || isLoading) return;

    let cancelled = false;

    async function fetchProfile() {
      setLoading(true);
      try {
        const profile = await getMyProfile();
        if (!cancelled) setUser(profile);
      } catch {
        // 401 → the Axios interceptor already redirected to /login
        if (!cancelled) clearUser();
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchProfile();
    return () => { cancelled = true; };
  // We intentionally run this only once on mount
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Logout ────────────────────────────────────────────────────────────────
  const logout = useCallback(async () => {
    await logoutUser();
    router.push('/login');
  }, [router]);

  return {
    user,
    isAuthenticated,
    isLoading,
    hasPermission,
    hasRole,
    logout,
  };
}
