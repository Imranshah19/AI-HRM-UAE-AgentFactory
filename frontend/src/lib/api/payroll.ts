/**
 * AI-HRMS — Payroll module API calls.
 */

import { api } from '@/lib/api';
import type {
  TaxSlab,
  TaxSlabCreate,
  TaxSlabUpdate,
  PayrollRun,
  PayrollRunCreate,
  PayrollRunDetail,
  PayrollRunListResponse,
  PayrollRecord,
  SalaryBreakdown,
  PayrollFilterParams,
  PayrollApprovalRequest,
} from '@/types/payroll';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function buildParams(filters: Partial<PayrollFilterParams>): URLSearchParams {
  const p = new URLSearchParams();
  const entries: Array<[string, string | number | undefined]> = [
    ['month',         filters.month],
    ['year',          filters.year],
    ['department_id', filters.department_id],
    ['status',        filters.status],
    ['employee_id',   filters.employee_id],
    ['page',          filters.page],
    ['page_size',     filters.page_size],
  ];
  entries.forEach(([k, v]) => {
    if (v !== undefined && v !== '' && v !== null) p.set(k, String(v));
  });
  return p;
}

// ─── Tax Slabs ────────────────────────────────────────────────────────────────

export async function getTaxSlabs(year: number): Promise<TaxSlab[]> {
  const res = await api.get<TaxSlab[]>(`/api/v1/payroll/tax-slabs?year=${year}`);
  return res.data;
}

export async function createTaxSlab(data: TaxSlabCreate): Promise<TaxSlab> {
  const res = await api.post<TaxSlab>('/api/v1/payroll/tax-slabs', data);
  return res.data;
}

export async function updateTaxSlab(id: string, data: TaxSlabUpdate): Promise<TaxSlab> {
  const res = await api.patch<TaxSlab>(`/api/v1/payroll/tax-slabs/${id}`, data);
  return res.data;
}

// ─── Payroll Runs ─────────────────────────────────────────────────────────────

export async function getPayrollRuns(
  filters: Partial<PayrollFilterParams> = {},
): Promise<PayrollRunListResponse> {
  const params = buildParams(filters);
  const res    = await api.get<PayrollRunListResponse>(
    `/api/v1/payroll/runs?${params.toString()}`,
  );
  return res.data;
}

export async function getPayrollRun(id: string): Promise<PayrollRunDetail> {
  const res = await api.get<PayrollRunDetail>(`/api/v1/payroll/runs/${id}`);
  return res.data;
}

export async function createPayrollRun(data: PayrollRunCreate): Promise<PayrollRun> {
  const res = await api.post<PayrollRun>('/api/v1/payroll/runs', data);
  return res.data;
}

export async function approvePayrollRun(
  id: string,
  payload: PayrollApprovalRequest,
): Promise<PayrollRun> {
  const res = await api.post<PayrollRun>(`/api/v1/payroll/runs/${id}/approve`, payload);
  return res.data;
}

export async function rejectPayrollRun(
  id: string,
  payload: PayrollApprovalRequest,
): Promise<PayrollRun> {
  const res = await api.post<PayrollRun>(`/api/v1/payroll/runs/${id}/reject`, payload);
  return res.data;
}

export function getBankFileUrl(runId: string): string {
  return `/api/v1/payroll/runs/${runId}/bank-file`;
}

// ─── Payslips ─────────────────────────────────────────────────────────────────

export async function getMyPayslips(): Promise<PayrollRecord[]> {
  const res = await api.get<PayrollRecord[]>('/api/v1/payroll/payslips/me');
  return res.data;
}

export async function getEmployeePayslips(employeeId: string): Promise<PayrollRecord[]> {
  const res = await api.get<PayrollRecord[]>(
    `/api/v1/payroll/payslips/employee/${employeeId}`,
  );
  return res.data;
}

export function getPayslipPdfUrl(recordId: string): string {
  return `/api/v1/payroll/payslips/${recordId}`;
}

// ─── Salary Preview ───────────────────────────────────────────────────────────

export async function getSalaryPreview(
  employeeId: string,
  month: number,
  year: number,
): Promise<SalaryBreakdown> {
  const res = await api.get<SalaryBreakdown>(
    `/api/v1/payroll/preview/${employeeId}?month=${month}&year=${year}`,
  );
  return res.data;
}
