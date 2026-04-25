// AI-HRMS — Payroll module TypeScript types

// ─── Enums ────────────────────────────────────────────────────────────────────

export type PayrollRunStatus =
  | 'draft'
  | 'processing'
  | 'processed'
  | 'approved'
  | 'paid'
  | 'cancelled'
  | 'rejected';

export type PayrollRecordStatus = 'pending' | 'processed' | 'paid' | 'on_hold';

export type ApprovalAction = 'approve' | 'reject';

// ─── Tax Slab ─────────────────────────────────────────────────────────────────

export interface TaxSlab {
  id:          string;
  year:        number;
  min_income:  number;
  max_income:  number | null;
  tax_rate:    number;  // 0.0 – 1.0
  fixed_tax:   number;
  description: string | null;
  is_active:   boolean;
  created_at:  string;
  updated_at:  string;
}

export interface TaxSlabCreate {
  year:        number;
  min_income:  number;
  max_income:  number | null;
  tax_rate:    number;
  fixed_tax:   number;
  description: string | null;
  is_active:   boolean;
}

export type TaxSlabUpdate = Partial<Omit<TaxSlabCreate, 'year'>>;

// ─── Employee Minimal ─────────────────────────────────────────────────────────

export interface EmployeeMinimal {
  id:                string;
  employee_code:     string;
  full_name:         string;
  department_name:   string | null;
  designation_title: string | null;
  photo_url:         string | null;
}

// ─── Payroll Run ──────────────────────────────────────────────────────────────

export interface PayrollRun {
  id:                    string;
  month:                 number;
  year:                  number;
  label:                 string | null;
  status:                PayrollRunStatus;
  total_employees:       number;
  total_gross:           number;
  total_net:             number;
  total_deductions:      number;
  total_eobi_employee:   number;
  total_eobi_employer:   number;
  total_income_tax:      number;
  processed_by:          string | null;
  approved_by:           string | null;
  run_at:                string | null;
  approved_at:           string | null;
  paid_at:               string | null;
  notes:                 string | null;
  celery_task_id:        string | null;
  created_at:            string;
  updated_at:            string;
}

export interface PayrollRunCreate {
  month:          number;
  year:           number;
  department_ids: string[] | null;
  notes:          string | null;
}

export interface PayrollRunListResponse {
  count:   number;
  results: PayrollRun[];
}

// ─── Payroll Record ───────────────────────────────────────────────────────────

export interface PayrollRecord {
  id:                   string;
  payroll_run_id:       string;
  employee_id:          string;
  employee:             EmployeeMinimal;

  // Earnings
  basic_salary:         number;
  house_rent_allowance: number;
  medical_allowance:    number;
  transport_allowance:  number;
  fuel_allowance:       number;
  other_allowances:     Record<string, number> | null;
  total_allowances:     number;
  gross_salary:         number;

  // Deductions
  eobi_employee:        number;
  eobi_employer:        number;
  sessi:                number;
  income_tax:           number;
  loan_deduction:       number;
  advance_deduction:    number;
  other_deductions:     Record<string, number> | null;
  total_deductions:     number;
  net_salary:           number;

  // Attendance
  working_days:         number;
  present_days:         number;
  absent_days:          number;
  late_days:            number;
  overtime_hours:       number | null;
  paid_leave_days:      number;
  unpaid_leave_days:    number;
  is_prorated:          boolean;

  payslip_url:          string | null;
  status:               PayrollRecordStatus;
  created_at:           string;
  updated_at:           string;
}

export interface PayrollRunDetail extends PayrollRun {
  records: PayrollRecord[];
}

// ─── Payslip Data ─────────────────────────────────────────────────────────────

export interface AllowanceItem {
  name:   string;
  amount: number;
}

export interface DeductionItem {
  name:   string;
  amount: number;
}

export interface PayslipData {
  record_id:       string;
  payroll_run_id:  string;
  month:           number;
  year:            number;
  employee_id:     string;
  employee_code:   string;
  full_name:       string;
  designation:     string | null;
  department:      string | null;
  cnic:            string | null;
  joining_date:    string | null;
  bank_name:       string | null;
  account_number:  string | null;
  iban:            string | null;
  basic_salary:    number;
  allowances:      AllowanceItem[];
  total_allowances: number;
  gross_salary:    number;
  deductions:      DeductionItem[];
  total_deductions: number;
  net_salary:      number;
  working_days:    number;
  present_days:    number;
  absent_days:     number;
  paid_leave_days: number;
  overtime_hours:  number | null;
  overtime_amount: number;
  generated_at:    string;
  payslip_url:     string | null;
}

// ─── Salary Preview ───────────────────────────────────────────────────────────

export interface SalaryBreakdown {
  employee_id:            string;
  employee_name:          string;
  month:                  number;
  year:                   number;
  basic_salary:           number;
  total_allowances:       number;
  gross_salary:           number;
  eobi_employee:          number;
  eobi_employer:          number;
  income_tax:             number;
  loan_deduction:         number;
  advance_deduction:      number;
  other_deductions_total: number;
  total_deductions:       number;
  net_salary:             number;
  working_days:           number;
  present_days:           number;
  absent_days:            number;
  overtime_hours:         number;
  overtime_amount:        number;
  effective_tax_rate:     number;
  annual_gross:           number;
  annual_tax:             number;
}

// ─── Bank File ────────────────────────────────────────────────────────────────

export interface BankFileEntry {
  employee_code:  string;
  employee_name:  string;
  bank_name:      string;
  account_number: string;
  iban:           string | null;
  net_salary:     number;
  reference:      string;
}

// ─── Filters ──────────────────────────────────────────────────────────────────

export interface PayrollFilterParams {
  month?:        number;
  year?:         number;
  department_id?: string;
  status?:       PayrollRunStatus;
  employee_id?:  string;
  page?:         number;
  page_size?:    number;
}

// ─── Approval ─────────────────────────────────────────────────────────────────

export interface PayrollApprovalRequest {
  action: ApprovalAction;
  notes?: string | null;
}
