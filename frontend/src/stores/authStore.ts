import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { User } from '@/types/auth';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  tenantSlug: string;
}

interface AuthActions {
  setUser: (user: User) => void;
  clearUser: () => void;
  setLoading: (loading: boolean) => void;
  setTenantSlug: (slug: string) => void;
  hasPermission: (module: string, action: string) => boolean;
  hasRole: (roleName: string) => boolean;
}

export type AuthStore = AuthState & AuthActions;

const safeLocalStorage = createJSONStorage(() => {
  if (typeof window !== 'undefined') return localStorage;
  return {
    getItem: () => null,
    setItem: () => {},
    removeItem: () => {},
  };
});

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // ── State ────────────────────────────────────────────────────────────
      user: null,
      isAuthenticated: false,
      isLoading: false,
      tenantSlug: 'system',

      // ── Actions ──────────────────────────────────────────────────────────
      setUser: (user: User) =>
        set({
          user,
          isAuthenticated: true,
          tenantSlug: user.tenant_slug ?? get().tenantSlug,
        }),

      clearUser: () =>
        set({ user: null, isAuthenticated: false }),

      setLoading: (isLoading: boolean) => set({ isLoading }),

      setTenantSlug: (tenantSlug: string) => set({ tenantSlug }),

      // ── Permission helpers ────────────────────────────────────────────────
      hasPermission: (module: string, action: string): boolean => {
        const { user } = get();
        if (!user) return false;
        if (user.is_superadmin) return true;
        return user.permissions.some(
          (p) => p.module_name === module && p.action === action,
        );
      },

      hasRole: (roleName: string): boolean => {
        const { user } = get();
        if (!user) return false;
        return user.roles.some((r) => r.name === roleName);
      },
    }),
    {
      name: 'hrms-auth',
      storage: safeLocalStorage,
      // Persist only the user + tenantSlug; flags are re-derived
      partialize: (state) => ({
        user: state.user,
        tenantSlug: state.tenantSlug,
      }),
      // Re-sync isAuthenticated when store rehydrates from localStorage
      onRehydrateStorage: () => (state) => {
        if (state?.user) {
          state.isAuthenticated = true;
        }
      },
    },
  ),
);
