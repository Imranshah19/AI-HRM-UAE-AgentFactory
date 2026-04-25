/**
 * AI-HRMS — Employee module TypeScript types.
 * Mirror of backend Pydantic schemas (employees/schemas.py).
 */

// ─── Enums ────────────────────────────────────────────────────────────────────

export type EmployeeStatus =
  | 'active'
  | 'inactive'
  | 'terminated'
  | 'resigned'
  | 'on_leave'
  | 'suspended';

export type ContractType =
  | 'permanent'
  | 'contract'
  | 'probation'
  | 'intern'
  | 'consultant';

export type GenderType =
  | 'male'
  | 'female'
  | 'other'
  | 'prefer_not_to_say';

export type MaritalStatus = 'single' | 'married' | 'divorced' | 'widowed';

export type WorkSchedule = 'full_time' | 'part_time' | 'remote' | 'hybrid';

export type DocumentType =
  | 'cnic_front'
  | 'cnic_back'
  | 'passport'
  | 'degree_certificate'
  | 'experience_letter'
  | 'cv_resume'
  | 'offer_letter'
  | 'contract'
  | 'medical_certificate'
  | 'visa'
  | 'work_permit'
  | 'noc'
  | 'other';

// ─── Nested objects ───────────────────────────────────────────────────────────

export interface AddressData {
  line1:       string;
  line2?:      string | null;
  city:        string;
  state?:      string | null;
  postal_code?: string | null;
  country:     string;
}

export interface EmergencyContactData {
  name:     string;
  relation: string;
  phone:    string;
  email?:   string | null;
}

export interface DepartmentMini {
  id:   string;
  name: string;
  code: string | null;
}

export interface DesignationMini {
  id:   string;
  name: string;
}

export interface ManagerMini {
  id:                string;
  employee_code:     string;
  full_name:         string;
  profile_photo_url: string | null;
}

export interface RoleMini {
  id:   string;
  name: string;
}

// ─── Department & Designation ─────────────────────────────────────────────────

export interface Department {
  id:             string;
  name:           string;
  code:           string | null;
  description:    string | null;
  parent_id:      string | null;
  is_active:      boolean;
  employee_count: number;
}

export interface Designation {
  id:            string;
  name:          string;
  title?:        string;        // alias for name used by some pages
  department_id: string | null;
  level:         string | null;
  grade:         string | null;
  min_salary:    number | null;
  max_salary:    number | null;
  is_active:     boolean;
}

// ─── Salary & Bank ────────────────────────────────────────────────────────────

export interface SalaryStructure {
  id:                    string;
  basic_salary:          number;
  house_rent_allowance:  number;
  medical_allowance:     number;
  transport_allowance:   number;
  other_allowances:      Record<string, number> | null;
  eobi_applicable:       boolean;
  sessi_applicable:      boolean;
  income_tax_applicable: boolean;
  effective_from:        string;
  effective_to:          string | null;
  total_allowances:      number;
  gross_salary:          number;
  revision_note?:        string | null;
  created_at?:           string | null;
}

export interface BankDetails {
  id:             string;
  bank_name:      string;
  account_title:  string;
  account_number: string;
  iban:           string | null;
  payment_method: string;
  is_primary:     boolean;
}

export interface SalaryBreakdown {
  basic_salary:         number;
  total_allowances:     number;
  gross_salary:         number;
  eobi_deduction:       number;
  sessi_deduction:      number;
  income_tax:           number;
  total_deductions:     number;
  net_salary:           number;
}

export interface SalaryWithBank {
  salary:          SalaryStructure | null;
  current_salary?: SalaryStructure | null;   // alias
  bank_details:    BankDetails[];
  salary_history?: SalaryStructure[];
}

// ─── Document ─────────────────────────────────────────────────────────────────

export interface EmployeeDocument {
  id:              string;
  doc_type:        DocumentType;
  doc_name:        string;
  file_url:        string;
  file_name:       string;
  file_size_bytes: number | null;
  mime_type:       string | null;
  expiry_date:     string | null;
  expires_at?:     string | null;   // alias for expiry_date
  uploaded_at?:    string | null;   // upload timestamp
  created_at?:     string | null;
  is_verified:     boolean;
  is_deleted:      boolean;
}

// ─── List item (table row) ────────────────────────────────────────────────────

export interface EmployeeListItem {
  id:                string;
  employee_code:     string;
  full_name:         string;
  work_email:        string | null;
  personal_email?:   string | null;
  department:        DepartmentMini | null;
  designation:       DesignationMini | null;
  employment_status: EmployeeStatus;
  contract_type:     ContractType;
  join_date:         string | null;
  date_of_joining?:  string | null;
  profile_photo_url: string | null;
  photo_url?:        string | null;
  department_name?:  string | null;
  designation_title?: string | null;
}

// ─── Full detail ──────────────────────────────────────────────────────────────

export interface EmployeeDetail {
  id:                string;
  employee_code:     string;
  first_name:        string;
  last_name:         string;
  full_name:         string;
  father_name:       string | null;
  cnic:              string | null;
  personal_email:    string | null;
  work_email:        string | null;
  phone:             string | null;
  gender:            GenderType | null;
  dob:               string | null;
  marital_status:    MaritalStatus | null;
  nationality:       string | null;
  address:           AddressData | null;
  emergency_contact: EmergencyContactData | null;
  profile_photo_url: string | null;
  // Employment
  department:        DepartmentMini | null;
  designation:       DesignationMini | null;
  manager:           ManagerMini | null;
  contract_type:     ContractType;
  work_schedule:     WorkSchedule;
  employment_status: EmployeeStatus;
  join_date:         string | null;
  probation_end_date: string | null;
  confirmation_date:  string | null;
  termination_date:   string | null;
  termination_reason: string | null;
  branch_location:    string | null;
  cost_center:        string | null;
  grade_level:        string | null;
  timezone:           string;
  // Compensation
  salary:       SalaryStructure | null;
  bank_details: BankDetails[];
  // Documents & roles
  documents: EmployeeDocument[];
  roles:     RoleMini[];
  hr_notes:  string | null;
  // Flat aliases used by some pages (mirrors nested objects above)
  department_id?:             string | null;
  designation_id?:            string | null;
  manager_id?:                string | null;
  department_name?:           string | null;
  designation_title?:         string | null;
  photo_url?:                 string | null;
  phone_number?:              string | null;
  middle_name?:               string | null;
  date_of_birth?:             string | null;
  date_of_joining?:           string | null;
  contract_end_date?:         string | null;
  blood_group?:               string | null;
  passport_number?:           string | null;
  address_line1?:             string | null;
  address_line2?:             string | null;
  city?:                      string | null;
  state?:                     string | null;
  country?:                   string | null;
  postal_code?:               string | null;
  emergency_contact_name?:    string | null;
  emergency_contact_phone?:   string | null;
  emergency_contact_relation?: string | null;
  // Additional computed / joined fields
  manager_name?:      string | null;
  created_at?:        string | null;
  updated_at?:        string | null;
  leave_balances?:    Array<{
    leave_type:       string;
    leave_type_id?:   string;
    leave_type_name?: string;
    total:            number;
    used:             number;
    remaining:        number;
  }> | null;
  attendance_summary?: {
    present_days:   number;
    absent_days:    number;
    late_days:      number;
    leave_days?:    number;
    overtime_hours: number;
  } | null;
}

// ─── Create / Update payloads ─────────────────────────────────────────────────

export interface EmployeeCreateData {
  first_name:           string;
  last_name:            string;
  father_name?:         string | null;
  cnic?:                string | null;
  personal_email?:      string | null;
  phone?:               string | null;
  gender?:              GenderType | null;
  dob?:                 string | null;
  marital_status?:      MaritalStatus | null;
  nationality?:         string | null;
  address?:             AddressData | null;
  emergency_contact?:   EmergencyContactData | null;
  employee_code?:       string | null;
  department_id?:       string | null;
  designation_id?:      string | null;
  manager_id?:          string | null;
  contract_type:        ContractType;
  work_schedule:        WorkSchedule;
  join_date?:           string | null;
  probation_end_date?:  string | null;
  confirmation_date?:   string | null;
  shift_id?:            string | null;
  timezone:             string;
  branch_location?:     string | null;
  cost_center?:         string | null;
  grade_level?:         string | null;
  basic_salary:         number;
  house_rent_allowance: number;
  medical_allowance:    number;
  transport_allowance:  number;
  other_allowances?:    Record<string, number> | null;
  eobi_applicable:      boolean;
  sessi_applicable:     boolean;
  income_tax_applicable: boolean;
  bank_name?:           string | null;
  account_title?:       string | null;
  account_number?:      string | null;
  iban?:                string | null;
  role_id?:             string | null;
  onboarding_notes?:    string | null;
  hr_notes?:            string | null;
}

export type EmployeeUpdateData = Partial<Omit<EmployeeCreateData, 'contract_type'>> & {
  contract_type?: ContractType;
};

export interface EmployeeStatusUpdate {
  employment_status: EmployeeStatus;
  reason?:          string | null;
  effective_date?:  string | null;
}

// ─── Filters ──────────────────────────────────────────────────────────────────

export interface EmployeeFilters {
  department_id?:  string;
  designation_id?: string;
  manager_id?:     string;
  status?:         EmployeeStatus;
  contract_type?:  ContractType;
  search?:         string;
  page:            number;
  page_size:       number;
}

// ─── Org chart ────────────────────────────────────────────────────────────────

export interface OrgChartNode {
  id:                string;
  employee_code:     string;
  full_name:         string;
  designation:       string | null;
  department:        string | null;
  profile_photo_url: string | null;
  photo_url?:        string | null;   // alias
  manager_id:        string | null;
  children:          OrgChartNode[];
}

// ─── Attendance ───────────────────────────────────────────────────────────────

export type AttendanceDayStatus =
  | 'present'
  | 'absent'
  | 'late'
  | 'half_day'
  | 'holiday'
  | 'weekend'
  | 'leave';

export interface AttendanceDayRecord {
  date:   string;
  status: AttendanceDayStatus;
}

export interface AttendanceSummary {
  present_days:   number;
  absent_days:    number;
  late_days:      number;
  overtime_hours: number;
  records:        AttendanceDayRecord[];
}

// ─── Leave ────────────────────────────────────────────────────────────────────

export interface LeaveBalance {
  leave_type: string;
  total:      number;
  used:       number;
  remaining:  number;
}

export interface LeaveRequest {
  id:         string;
  leave_type: string;
  start_date: string;
  end_date:   string;
  days:       number;
  status:     'pending' | 'approved' | 'rejected';
  reason:     string | null;
}
