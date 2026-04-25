// AI-HRMS — Leave module TypeScript types

export type LeaveStatus = 'pending' | 'approved' | 'rejected' | 'cancelled';

// ─── Leave Type ───────────────────────────────────────────────────────────────

export interface LeaveType {
  id:                     string;
  name:                   string;
  days_allowed:           number;
  is_paid:                boolean;
  carry_forward:          boolean;
  max_carry_forward_days: number;
  requires_document:      boolean;
  color:                  string;
  is_active:              boolean;
}

export interface LeaveTypeCreate {
  name:                   string;
  days_allowed:           number;
  is_paid:                boolean;
  carry_forward:          boolean;
  max_carry_forward_days: number;
  requires_document:      boolean;
  color:                  string;
  is_active:              boolean;
}

export type LeaveTypeUpdate = Partial<LeaveTypeCreate>;

// ─── Employee Minimal ─────────────────────────────────────────────────────────

export interface EmployeeMinimal {
  id:                string;
  full_name:         string;
  employee_code:     string;
  photo_url?:        string | null;
  department_name?:  string | null;
  designation_title?: string | null;
}

// ─── Leave Request ────────────────────────────────────────────────────────────

export interface LeaveRequest {
  id:               string;
  leave_type_id:    string;
  leave_type:       LeaveType;
  employee_id:      string;
  employee:         EmployeeMinimal;
  start_date:       string;   // ISO date yyyy-MM-dd
  end_date:         string;
  days:             number;
  reason:           string;
  document_url?:    string | null;
  status:           LeaveStatus;
  approved_by?:     string | null;
  approved_by_name?: string | null;
  approved_at?:     string | null;
  rejection_reason?: string | null;
  cancelled_at?:    string | null;
  created_at:       string;
  updated_at:       string;
}

export interface LeaveRequestListItem {
  id:               string;
  leave_type_id:    string;
  leave_type_name:  string;
  leave_type_color: string;
  employee_id:      string;
  employee_name:    string;
  employee_code:    string;
  department_name?: string | null;
  start_date:       string;
  end_date:         string;
  days:             number;
  reason:           string;
  status:           LeaveStatus;
  approved_by_name?: string | null;
  rejection_reason?: string | null;
  created_at:       string;
}

export interface LeaveRequestCreate {
  leave_type_id: string;
  start_date:    string;
  end_date:      string;
  reason:        string;
  document_url?: string;
  employee_id?:  string;
}

export interface LeaveRequestUpdate {
  start_date?:   string;
  end_date?:     string;
  reason?:       string;
  document_url?: string;
}

export interface LeaveApprovalRequest {
  action:            'approve' | 'reject';
  rejection_reason?: string;
}

// ─── Balance ──────────────────────────────────────────────────────────────────

export interface LeaveBalanceItem {
  leave_type_id:    string;
  leave_type_name:  string;
  leave_type_color: string;
  is_paid:          boolean;
  total_days:       number;
  used_days:        number;
  remaining_days:   number;
  carried_forward:  number;
}

export interface LeaveBalanceResponse {
  employee_id:   string;
  employee_name: string;
  year:          number;
  balances:      LeaveBalanceItem[];
}

// ─── Calendar ─────────────────────────────────────────────────────────────────

export interface LeaveCalendarEntry {
  date:             string;   // ISO date
  employee_id:      string;
  employee_name:    string;
  employee_code:    string;
  photo_url?:       string | null;
  leave_type_id:    string;
  leave_type_name:  string;
  leave_type_color: string;
  status:           LeaveStatus;
}

// ─── Public Holiday ───────────────────────────────────────────────────────────

export interface PublicHoliday {
  id:           string;
  date:         string;
  name:         string;
  is_recurring: boolean;
}

export interface PublicHolidayCreate {
  date:         string;
  name:         string;
  is_recurring: boolean;
}

// ─── Filters / Pagination ─────────────────────────────────────────────────────

export interface LeaveFilterParams {
  employee_id?:   string;
  department_id?: string;
  leave_type_id?: string;
  status?:        LeaveStatus;
  start_date?:    string;
  end_date?:      string;
  page?:          number;
  page_size?:     number;
}

export interface PaginatedLeaveRequests {
  count:   number;
  results: LeaveRequestListItem[];
}
