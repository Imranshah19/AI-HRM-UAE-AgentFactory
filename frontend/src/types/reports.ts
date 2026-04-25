// AI-HRMS — Reports TypeScript types

export interface UpcomingBirthday {
  employee_id: string;
  full_name:   string;
  birthday:    string;   // MM-DD
  days_until:  number;
  department:  string | null;
}

export interface DashboardStats {
  total_employees:    number;
  present_today:      number;
  pending_leaves:     number;
  open_positions:     number;
  payroll_due:        boolean;
  upcoming_birthdays: UpcomingBirthday[];
}

export interface DeptHeadcount {
  department: string;
  count:      number;
  percentage: number;
}

export interface HeadcountReport {
  total:              number;
  by_department:      DeptHeadcount[];
  by_contract_type:   Array<{ contract_type: string; count: number }>;
  by_gender:          Array<{ gender: string; count: number }>;
  by_status:          Array<{ status: string; count: number }>;
}

export interface TurnoverMonth {
  month:         string;
  month_num:     number;
  resignations:  number;
  terminations:  number;
  total_exits:   number;
  headcount:     number;
  turnover_rate: number;
}

export interface TurnoverReport {
  year:        number;
  months:      TurnoverMonth[];
  total_exits: number;
  avg_rate:    number;
}

export interface DeptAttendance {
  department:     string;
  total_expected: number;
  present:        number;
  absent:         number;
  late:           number;
  present_pct:    number;
  absent_pct:     number;
  late_pct:       number;
}

export interface AttendanceReport {
  month:       number;
  year:        number;
  by_dept:     DeptAttendance[];
  daily_trend: Array<{ date: string; present: number; absent: number; late: number }>;
}

export interface PayrollMonth {
  month:     string;
  month_num: number;
  gross:     number;
  net:       number;
  tax:       number;
  eobi:      number;
  headcount: number;
}

export interface PayrollReport {
  year:   number;
  months: PayrollMonth[];
  totals: { gross: number; net: number; tax: number; eobi: number };
}

export interface LeaveByType {
  leave_type: string;
  total_days: number;
  employees:  number;
}

export interface LeaveDeptRow {
  department:  string;
  total_days:  number;
  avg_per_emp: number;
}

export interface LeaveReport {
  year:          number;
  by_type:       LeaveByType[];
  by_department: LeaveDeptRow[];
  monthly_trend: Array<{ month: string; month_num: number; days_taken: number }>;
}

export interface RecruitmentReport {
  year:               number;
  total_postings:     number;
  total_applications: number;
  total_hires:        number;
  avg_time_to_hire:   number;
  monthly:            Array<{ month: string; month_num: number; applications: number; hires: number }>;
  by_department:      Array<{ department: string; applications: number; hires: number }>;
}
