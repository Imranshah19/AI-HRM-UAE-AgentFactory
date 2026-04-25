/**
 * AI-HRMS — Auth helper functions.
 *
 * These are plain async functions (not hooks).
 * Call them from event handlers or useEffect inside Client Components.
 */

import type { AxiosError } from 'axios';
import { api } from './api';
import type { User } from '@/types/auth';

// ─── Login ──────────────────────────────────────────────────────────────────

export async function loginUser(email: string, password: string): Promise<User> {
  // POST /auth/login sets access_token + refresh_token httpOnly cookies
  await api.post('/api/v1/auth/login', { email, password });

  // Fetch the full user profile so the store has complete data
  return getMyProfile();
}

// ─── Logout ─────────────────────────────────────────────────────────────────

export async function logoutUser(): Promise<void> {
  try {
    await api.post('/api/v1/auth/logout');
  } catch {
    // Swallow errors — we always clear local state
  } finally {
    const { useAuthStore } = await import('@/stores/authStore');
    useAuthStore.getState().clearUser();
  }
}

// ─── Refresh ────────────────────────────────────────────────────────────────

export async function refreshToken(): Promise<boolean> {
  try {
    await api.post('/api/v1/auth/refresh');
    return true;
  } catch {
    return false;
  }
}

// ─── Profile ────────────────────────────────────────────────────────────────

export async function getMyProfile(): Promise<User> {
  const response = await api.get<User>('/api/v1/auth/me');
  return response.data;
}

// ─── Change password ─────────────────────────────────────────────────────────

export async function changePassword(
  oldPassword: string,
  newPassword: string,
): Promise<void> {
  await api.post('/api/v1/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword,
  });
}

// ─── Error extractor ────────────────────────────────────────────────────────

export function extractApiError(error: unknown): string {
  const axiosErr = error as AxiosError<{
    detail: string | { msg: string }[];
  }>;

  const detail = axiosErr?.response?.data?.detail;

  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((d) => d.msg).join(', ');
  }

  return 'An unexpected error occurred. Please try again.';
}
