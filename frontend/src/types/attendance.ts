// AI-HRMS — Attendance & Time Tracking TypeScript types

export type AttendanceStatus =
  | 'present'
  | 'late'
  | 'absent'
  | 'half_day'
  | 'on_leave'
  | 'holiday'
  | 'weekend';

export type CheckInSource = 'manual' | 'mobile' | 'biometric' | 'geo';
export type AdjustmentStatus = 'pending' | 'approved' | 'rejected';

// ─── Shift ────────────────────────────────────────────────────────────────────

export interface Shift {
  id:                   string;
  name:                 string;
  start_time:           string;   // "HH:MM:SS"
  end_time:             string;
  grace_period_minutes: number;
  total_hours:          number;
  is_active:            boolean;
}

export interface ShiftCreate {
  name:                 string;
  start_time:           string;
  end_time:             string;
  grace_period_minutes: number;
  is_active:            boolean;
}

// ─── Location ─────────────────────────────────────────────────────────────────

export interface LocationData {
  lat:      number;
  lng:      number;
  address?: string;
}

// ─── Check-in / Check-out ─────────────────────────────────────────────────────

export interface AttendanceCheckInRequest {
  source?:   CheckInSource;
  location?: LocationData;
  notes?:    string;
}

export interface AttendanceCheckOutRequest {
  notes?: string;
}

// ─── Employee Minimal ─────────────────────────────────────────────────────────

export interface EmployeeMinimal {
  id:                string;
  full_name:         string;
  employee_code:     string;
  photo_url?:        string | null;
  department_name?:  string | null;
  designation_title?: string | null;
}

// ─── Attendance Record ────────────────────────────────────────────────────────

export interface AttendanceRecord {
  id:               string;
  employee_id:      string;
  employee:         EmployeeMinimal;
  date:             string;          // ISO date
  check_in?:        string | null;   // ISO datetime
  check_out?:       string | null;
  working_hours?:   number | null;
  overtime_hours?:  number | null;
  status:           AttendanceStatus;
  source:           CheckInSource;
  location_lat?:    number | null;
  location_lng?:    number | null;
  location_address?: string | null;
  notes?:           string | null;
  is_manual:        boolean;
  shift_id?:        string | null;
  created_at:       string;
  updated_at:       string;
}

export interface AttendanceRecordListItem {
  id:             string;
  employee_id:    string;
  employee_name:  string;
  employee_code:  string;
  department_name?: string | null;
  date:           string;
  check_in?:      string | null;
  check_out?:     string | null;
  working_hours?: number | null;
  overtime_hours?: number | null;
  status:         AttendanceStatus;
  source:         CheckInSource;
  is_manual:      boolean;
}

export interface PaginatedAttendanceRecords {
  count:   number;
  results: AttendanceRecordListItem[];
}

// ─── Manual Entry & Adjustment ────────────────────────────────────────────────

export interface AttendanceManualEntryRequest {
  employee_id: string;
  date:        string;
  check_in:    string;
  check_out?:  string;
  reason:      string;
  source?:     CheckInSource;
}

export interface AttendanceAdjustmentRequest {
  attendance_id:   string;
  new_check_in:    string;
  new_check_out?:  string;
  reason:          string;
}

export interface AdjustmentRecord {
  id:                   string;
  attendance_id:        string;
  employee_id:          string;
  employee_name:        string;
  original_check_in?:   string | null;
  original_check_out?:  string | null;
  requested_check_in:   string;
  requested_check_out?: string | null;
  reason:               string;
  status:               AdjustmentStatus;
  reviewed_by?:         string | null;
  review_note?:         string | null;
  reviewed_at?:         string | null;
  created_at:           string;
}

// ─── Summary ──────────────────────────────────────────────────────────────────

export interface AttendanceSummary {
  employee_id:           string;
  employee_name:         string;
  month:                 number;
  year:                  number;
  total_working_days:    number;
  present_days:          number;
  absent_days:           number;
  late_days:             number;
  half_days:             number;
  leave_days:            number;
  holiday_days:          number;
  total_working_hours:   number;
  total_overtime_hours:  number;
  attendance_percentage: number;
}

// ─── Timesheet ────────────────────────────────────────────────────────────────

export interface TimesheetRow {
  date:           string;
  day_name:       string;
  check_in?:      string | null;
  check_out?:     string | null;
  working_hours?: number | null;
  overtime_hours?: number | null;
  status:         AttendanceStatus;
  is_weekend:     boolean;
  is_holiday:     boolean;
  holiday_name?:  string | null;
  notes?:         string | null;
  attendance_id?: string | null;
}

export interface TimesheetResponse {
  employee_id:          string;
  employee_name:        string;
  month:                number;
  year:                 number;
  rows:                 TimesheetRow[];
  total_working_hours:  number;
  total_overtime_hours: number;
  total_present_days:   number;
}

// ─── Live / WebSocket ─────────────────────────────────────────────────────────

export interface LiveAttendanceEntry {
  employee_id:     string;
  employee_name:   string;
  photo_url?:      string | null;
  department_name?: string | null;
  action:          'check_in' | 'check_out';
  time:            string;
  check_in_time?:  string | null;
  status:          AttendanceStatus;
  // frontend-only: unique key for animation
  _key?:           string;
}

export interface LiveDashboardStats {
  present_now:   number;
  total_active:  number;
  late_today:    number;
  absent_today:  number;
}

// ─── Filters ──────────────────────────────────────────────────────────────────

export interface AttendanceFilterParams {
  employee_id?:   string;
  department_id?: string;
  date?:          string;
  date_from?:     string;
  date_to?:       string;
  status?:        AttendanceStatus;
  source?:        CheckInSource;
  page?:          number;
  page_size?:     number;
}
