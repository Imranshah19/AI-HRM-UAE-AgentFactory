/**
 * AI-HRMS — Employee module API calls.
 * All functions return typed data; raw Axios calls are centralised here.
 */

import { api } from '@/lib/api';
import type { PaginatedResponse } from '@/types/api';
import type {
  Department,
  Designation,
  EmployeeCreateData,
  EmployeeDetail,
  EmployeeFilters,
  EmployeeListItem,
  EmployeeStatusUpdate,
  EmployeeUpdateData,
  OrgChartNode,
  SalaryStructure,
  SalaryWithBank,
} from '@/types/employee';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function buildFilterParams(filters: Partial<EmployeeFilters>): URLSearchParams {
  const params = new URLSearchParams();
  const entries: Array<[string, string | number | undefined]> = [
    ['department_id',  filters.department_id],
    ['designation_id', filters.designation_id],
    ['manager_id',     filters.manager_id],
    ['status',         filters.status],
    ['contract_type',  filters.contract_type],
    ['search',         filters.search],
    ['page',           filters.page],
    ['page_size',      filters.page_size],
  ];
  entries.forEach(([key, val]) => {
    if (val !== undefined && val !== '' && val !== null) {
      params.set(key, String(val));
    }
  });
  return params;
}

// ─── Employee CRUD ────────────────────────────────────────────────────────────

export async function getEmployees(
  filters: Partial<EmployeeFilters> = {},
): Promise<PaginatedResponse<EmployeeListItem>> {
  const params = buildFilterParams(filters);
  const res = await api.get<PaginatedResponse<EmployeeListItem>>(
    `/api/v1/employees?${params.toString()}`,
  );
  return res.data;
}

export async function getEmployee(id: string): Promise<EmployeeDetail> {
  const res = await api.get<EmployeeDetail>(`/api/v1/employees/${id}`);
  return res.data;
}

export async function createEmployee(
  data: EmployeeCreateData,
): Promise<{ id: string; employee_code: string; work_email: string | null; full_name: string }> {
  const res = await api.post('/api/v1/employees', data);
  return res.data;
}

export async function updateEmployee(
  id: string,
  data: EmployeeUpdateData,
): Promise<EmployeeDetail> {
  const res = await api.patch<EmployeeDetail>(`/api/v1/employees/${id}`, data);
  return res.data;
}

export async function updateEmployeeStatus(
  id: string,
  payload: EmployeeStatusUpdate,
): Promise<EmployeeDetail> {
  const res = await api.patch<EmployeeDetail>(`/api/v1/employees/${id}/status`, payload);
  return res.data;
}

// ─── Salary ───────────────────────────────────────────────────────────────────

export async function getEmployeeSalary(id: string): Promise<SalaryWithBank> {
  const res = await api.get<SalaryWithBank>(`/api/v1/employees/${id}/salary`);
  return res.data;
}

export async function updateEmployeeSalary(
  id: string,
  data: {
    basic_salary:          number;
    house_rent_allowance:  number;
    medical_allowance:     number;
    transport_allowance:   number;
    other_allowances?:     Record<string, number> | null;
    eobi_applicable:       boolean;
    sessi_applicable:      boolean;
    income_tax_applicable: boolean;
    effective_from:        string;
    revision_note?:        string | null;
  },
): Promise<SalaryStructure> {
  const res = await api.patch<SalaryStructure>(`/api/v1/employees/${id}/salary`, data);
  return res.data;
}

// ─── Documents ────────────────────────────────────────────────────────────────

export async function uploadDocument(
  employeeId: string,
  docType:    string,
  file:       File,
): Promise<import('@/types/employee').EmployeeDocument> {
  const form = new FormData();
  form.append('file', file);
  form.append('doc_type', docType);

  const res = await api.post(
    `/api/v1/employees/${employeeId}/documents`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return res.data;
}

export async function deleteDocument(
  employeeId: string,
  docId:      string,
): Promise<void> {
  await api.delete(`/api/v1/employees/${employeeId}/documents/${docId}`);
}

// ─── Org chart ────────────────────────────────────────────────────────────────

export async function getOrgChart(): Promise<OrgChartNode[]> {
  const res = await api.get<OrgChartNode[]>('/api/v1/employees/org-chart');
  return res.data;
}

// ─── Export ───────────────────────────────────────────────────────────────────

export async function exportEmployees(
  filters: Partial<EmployeeFilters> = {},
): Promise<Blob> {
  const params = buildFilterParams(filters);
  const res = await api.get(`/api/v1/employees/export?${params.toString()}`, {
    responseType: 'blob',
  });
  return res.data as Blob;
}

// ─── Departments & Designations ───────────────────────────────────────────────

export async function getDepartments(): Promise<Department[]> {
  const res = await api.get<Department[]>('/api/v1/departments');
  return res.data;
}

export async function getDesignations(
  departmentId?: string,
): Promise<Designation[]> {
  const params = departmentId ? `?department_id=${departmentId}` : '';
  const res = await api.get<Designation[]>(`/api/v1/designations${params}`);
  return res.data;
}
