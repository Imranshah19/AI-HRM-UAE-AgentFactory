// ─── Lookup / Reference Types ─────────────────────────────────────────────────

export interface Department {
  id: string;
  name: string;
  code: string;
  parent_id?: string;
}

export interface Branch {
  id: string;
  name: string;
  city: string;
  country: string;
  timezone: string;
}

export interface Employee {
  id: string;
  full_name: string;
  designation: string;
  department: string;
  avatar_url?: string;
}

export interface Role {
  id: string;
  name: string;
  description: string;
  level: "super_admin" | "hr_manager" | "recruiter" | "manager" | "employee";
}

export interface Shift {
  id: string;
  name: string;
  start_time: string;
  end_time: string;
}

export interface SalaryStructure {
  id: string;
  name: string;
  description: string;
}

export interface HRModule {
  id: string;
  name: string;
  icon: string;
  description: string;
}

// ─── Form Step Metadata ───────────────────────────────────────────────────────

export interface FormStep {
  id: number;
  key: "basic_info" | "employment" | "compensation" | "documents" | "access";
  label: string;
  description: string;
  icon: string;
  isCompleted: boolean;
  hasError: boolean;
}

// ─── API Response Types ───────────────────────────────────────────────────────

export interface CreateEmployeeResponse {
  success: boolean;
  employee_id: string;
  employee_number: string;
  message: string;
  work_email?: string;
}

export interface ValidationError {
  field: string;
  message: string;
}

export interface ApiError {
  code: string;
  message: string;
  details?: ValidationError[];
}

// ─── Salary Calculation ───────────────────────────────────────────────────────

export interface SalaryBreakdown {
  gross_salary: number;
  basic_salary: number;
  total_allowances: number;
  house_rent_allowance: number;
  medical_allowance: number;
  transport_allowance: number;
  fuel_allowance: number;
  utility_allowance: number;
  other_allowances: number;
  eobi_deduction: number;
  sessi_deduction: number;
  estimated_income_tax: number;
  net_salary: number;
}

// ─── Document Upload ──────────────────────────────────────────────────────────

export interface DocumentUploadItem {
  id: string;
  doc_type: string;
  doc_name: string;
  file?: File;
  file_name?: string;
  file_size?: number;
  expiry_date?: string;
  is_mandatory: boolean;
  upload_status: "pending" | "uploading" | "uploaded" | "error";
  preview_url?: string;
}
