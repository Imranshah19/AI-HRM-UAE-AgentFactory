'use client';

/**
 * AI-HRMS — Axios API client.
 *
 * Features:
 *  - withCredentials: true  → sends httpOnly cookies on every request
 *  - Request interceptor    → adds X-Tenant-Slug from auth store
 *  - Response interceptor   → retries once after 401 via /auth/refresh,
 *                             then clears auth and redirects to /login
 *  - 429 handling           → shows a toast
 */

import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios';
import { toast } from 'sonner';

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ─── Refresh-queue state ────────────────────────────────────────────────────
// When a 401 fires while we're already refreshing, queue the retries so we
// only issue one refresh call instead of flooding the endpoint.

let isRefreshing = false;

type QueueEntry = {
  resolve: () => void;
  reject: (err: unknown) => void;
};

let failedQueue: QueueEntry[] = [];

function flushQueue(error: unknown): void {
  failedQueue.forEach(({ resolve, reject }) =>
    error ? reject(error) : resolve(),
  );
  failedQueue = [];
}

// ─── Axios instance ─────────────────────────────────────────────────────────

const api: AxiosInstance = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30_000,
});

// ─── Request interceptor — tenant header ─────────────────────────────────────

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
    try {
      // Lazy import avoids circular-dependency warnings at module load
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const { useAuthStore } = require('@/stores/authStore') as {
        useAuthStore: { getState: () => { tenantSlug: string } };
      };
      const slug = useAuthStore.getState().tenantSlug;
      if (slug) {
        config.headers['X-Tenant-Slug'] = slug;
      }
    } catch {
      // SSR — store not available; middleware will use default tenant
    }
    return config;
  },
  (error: unknown) => Promise.reject(error),
);

// ─── Response interceptor — 401 refresh + 429 toast ─────────────────────────

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // ── 429 Rate Limit ──────────────────────────────────────────────────────
    if (error.response?.status === 429) {
      toast.error('Too many requests — please slow down.');
      return Promise.reject(error);
    }

    // ── 401 Unauthorized ────────────────────────────────────────────────────
    if (error.response?.status === 401 && !original._retry) {
      // Never refresh inside the refresh or login call itself
      const isAuthEndpoint =
        original.url?.includes('/auth/refresh') ||
        original.url?.includes('/auth/login');
      if (isAuthEndpoint) {
        return Promise.reject(error);
      }

      // While a refresh is already in flight, queue this retry
      if (isRefreshing) {
        return new Promise<AxiosResponse>((resolve, reject) => {
          failedQueue.push({
            resolve: () => resolve(api(original)),
            reject,
          });
        });
      }

      original._retry = true;
      isRefreshing = true;

      try {
        await api.post('/api/v1/auth/refresh');
        flushQueue(null);
        return api(original);
      } catch (refreshError) {
        flushQueue(refreshError);

        // Clear auth state and bounce to login
        try {
          // eslint-disable-next-line @typescript-eslint/no-require-imports
          const { useAuthStore } = require('@/stores/authStore') as {
            useAuthStore: { getState: () => { clearUser: () => void } };
          };
          useAuthStore.getState().clearUser();
        } catch {
          // ignore
        }

        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  },
);

export default api;
export { api };
