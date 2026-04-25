'use client';

import { useAuthStore } from '@/stores/authStore';

/**
 * usePermission — granular permission check hook.
 *
 * @param module  The module_name from the Permission model
 *                e.g. "employee_management", "payroll", "leave"
 * @param action  The action from the Permission model
 *                e.g. "read", "create", "update", "delete", "approve", "export"
 * @returns       true if the authenticated user holds this permission
 *
 * Usage:
 *   const canCreateEmployee = usePermission('employee_management', 'create');
 *   if (!canCreateEmployee) return <AccessDenied />;
 */
export function usePermission(module: string, action: string): boolean {
  return useAuthStore((state) => state.hasPermission(module, action));
}

/**
 * useRole — role membership check hook.
 *
 * @param roleName  Role name, e.g. "Admin", "HR Manager"
 * @returns         true if the authenticated user holds this role
 */
export function useRole(roleName: string): boolean {
  return useAuthStore((state) => state.hasRole(roleName));
}
