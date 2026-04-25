'use client';

/**
 * AI-HRMS — Employee TanStack Query hooks.
 *
 * Query key convention:
 *   ['employees']           → all employees (invalidated on mutations)
 *   ['employees', filters]  → paginated list
 *   ['employee', id]        → single detail
 *   ['employee', id, 'salary'] → salary + bank
 *   ['departments']         → all departments
 *   ['designations', deptId?] → designations (filtered or all)
 *   ['org-chart']           → org chart tree
 */

import { useCallback } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';

import * as employeeApi from '@/lib/api/employees';
import { extractApiError } from '@/lib/auth';
import type {
  EmployeeFilters,
  EmployeeStatusUpdate,
  EmployeeUpdateData,
} from '@/types/employee';

// ─── Query keys ───────────────────────────────────────────────────────────────

export const empKeys = {
  all:         () => ['employees'] as const,
  lists:       () => [...empKeys.all(), 'list'] as const,
  list:        (f: Partial<EmployeeFilters>) => [...empKeys.lists(), f] as const,
  detail:      (id: string) => ['employee', id] as const,
  salary:      (id: string) => ['employee', id, 'salary'] as const,
  orgChart:    () => ['org-chart'] as const,
  departments: () => ['departments'] as const,
  designations:(deptId?: string) => ['designations', deptId ?? 'all'] as const,
};

// ─── List ─────────────────────────────────────────────────────────────────────

export function useEmployeeList(filters: Partial<EmployeeFilters> = {}) {
  return useQuery({
    queryKey:  empKeys.list(filters),
    queryFn:   () => employeeApi.getEmployees(filters),
    staleTime: 30_000,
    placeholderData: (prev) => prev,   // keep previous data while loading new page
  });
}

// ─── Single detail ────────────────────────────────────────────────────────────

export function useEmployee(id: string) {
  return useQuery({
    queryKey:  empKeys.detail(id),
    queryFn:   () => employeeApi.getEmployee(id),
    staleTime: 60_000,
    enabled:   !!id,
  });
}

// ─── Salary ───────────────────────────────────────────────────────────────────

export function useEmployeeSalary(id: string) {
  return useQuery({
    queryKey: empKeys.salary(id),
    queryFn:  () => employeeApi.getEmployeeSalary(id),
    staleTime: 120_000,
    enabled:   !!id,
  });
}

// ─── Create ───────────────────────────────────────────────────────────────────

export function useCreateEmployee() {
  const queryClient = useQueryClient();
  const router      = useRouter();

  return useMutation({
    mutationFn: employeeApi.createEmployee,
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: empKeys.all() });
      toast.success(`Employee ${created.employee_code} created!`);
      router.push(`/employees/${created.id}`);
    },
    onError: (error: unknown) => {
      toast.error(extractApiError(error));
    },
  });
}

// ─── Update ───────────────────────────────────────────────────────────────────

export function useUpdateEmployee(id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: EmployeeUpdateData) => employeeApi.updateEmployee(id, data),
    onMutate: async (newData) => {
      await queryClient.cancelQueries({ queryKey: empKeys.detail(id) });
      const snapshot = queryClient.getQueryData(empKeys.detail(id));
      // Optimistic update
      queryClient.setQueryData(empKeys.detail(id), (old: unknown) => ({
        ...(old as object),
        ...newData,
      }));
      return { snapshot };
    },
    onError: (error: unknown, _vars, context) => {
      if (context?.snapshot) {
        queryClient.setQueryData(empKeys.detail(id), context.snapshot);
      }
      toast.error(extractApiError(error));
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(empKeys.detail(id), updated);
      queryClient.invalidateQueries({ queryKey: empKeys.lists() });
      toast.success('Employee updated.');
    },
  });
}

// ─── Status update ────────────────────────────────────────────────────────────

export function useUpdateEmployeeStatus(id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: EmployeeStatusUpdate) =>
      employeeApi.updateEmployeeStatus(id, payload),
    onMutate: async ({ employment_status }) => {
      await queryClient.cancelQueries({ queryKey: empKeys.detail(id) });
      const snapshot = queryClient.getQueryData(empKeys.detail(id));
      queryClient.setQueryData(empKeys.detail(id), (old: unknown) => ({
        ...(old as object),
        employment_status,
      }));
      return { snapshot };
    },
    onError: (error: unknown, _vars, context) => {
      if (context?.snapshot) {
        queryClient.setQueryData(empKeys.detail(id), context.snapshot);
      }
      toast.error(extractApiError(error));
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(empKeys.detail(id), updated);
      queryClient.invalidateQueries({ queryKey: empKeys.lists() });
      toast.success(`Status changed to ${updated.employment_status}.`);
    },
  });
}

// ─── Document upload ──────────────────────────────────────────────────────────

export function useUploadDocument(employeeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ docType, file }: { docType: string; file: File }) =>
      employeeApi.uploadDocument(employeeId, docType, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: empKeys.detail(employeeId) });
      toast.success('Document uploaded.');
    },
    onError: (error: unknown) => {
      toast.error(extractApiError(error));
    },
  });
}

// ─── Document delete ──────────────────────────────────────────────────────────

export function useDeleteDocument(employeeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (docId: string) =>
      employeeApi.deleteDocument(employeeId, docId),
    onMutate: async (docId) => {
      await queryClient.cancelQueries({ queryKey: empKeys.detail(employeeId) });
      const snapshot = queryClient.getQueryData(empKeys.detail(employeeId));
      // Optimistic remove
      queryClient.setQueryData(empKeys.detail(employeeId), (old: unknown) => {
        if (!old || typeof old !== 'object') return old;
        const emp = old as { documents?: Array<{ id: string }> };
        return {
          ...emp,
          documents: emp.documents?.filter((d) => d.id !== docId),
        };
      });
      return { snapshot };
    },
    onError: (error: unknown, _docId, context) => {
      if (context?.snapshot) {
        queryClient.setQueryData(empKeys.detail(employeeId), context.snapshot);
      }
      toast.error(extractApiError(error));
    },
    onSuccess: () => {
      toast.success('Document deleted.');
    },
  });
}

// ─── Org chart ────────────────────────────────────────────────────────────────

export function useOrgChart() {
  return useQuery({
    queryKey: empKeys.orgChart(),
    queryFn:  employeeApi.getOrgChart,
    staleTime: 300_000,
  });
}

// ─── Departments ──────────────────────────────────────────────────────────────

export function useDepartments() {
  return useQuery({
    queryKey: empKeys.departments(),
    queryFn:  employeeApi.getDepartments,
    staleTime: 300_000,
  });
}

// ─── Designations ─────────────────────────────────────────────────────────────

export function useDesignations(departmentId?: string) {
  return useQuery({
    queryKey: empKeys.designations(departmentId),
    queryFn:  () => employeeApi.getDesignations(departmentId),
    staleTime: 300_000,
  });
}

// ─── Export helper ────────────────────────────────────────────────────────────

export function useExportEmployees() {
  return useCallback(async (filters: Partial<EmployeeFilters> = {}) => {
    try {
      const blob = await employeeApi.exportEmployees(filters);
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = `employees_${new Date().toISOString().slice(0, 10)}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Export started.');
    } catch (error: unknown) {
      toast.error(extractApiError(error));
    }
  }, []);
}
