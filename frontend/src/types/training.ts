// AI-HRMS — Training Management TypeScript types

// ─── Enums ────────────────────────────────────────────────────────────────────

export type TrainingMode =
  | 'online' | 'in_person' | 'hybrid' | 'self_paced';

export type TrainingStatus =
  | 'planned' | 'registration_open' | 'ongoing' | 'completed' | 'cancelled';

export type EnrollmentStatus =
  | 'enrolled' | 'in_progress' | 'completed' | 'failed' | 'absent' | 'dropped';

// ─── Nested ───────────────────────────────────────────────────────────────────

export interface EmployeeMinimal {
  id:            string;
  employee_code: string;
  full_name:     string;
  department?:   string | null;
  designation?:  string | null;
}

// ─── Training Program ─────────────────────────────────────────────────────────

export interface TrainingProgram {
  id:                          string;
  tenant_id:                   string;
  title:                       string;
  description:                 string | null;
  category:                    string | null;
  skills_covered:              string[] | null;
  trainer:                     string | null;
  trainer_id:                  string | null;
  mode:                        TrainingMode;
  venue:                       string | null;
  meeting_link:                string | null;
  start_date:                  string | null;
  end_date:                    string | null;
  duration_hours:              number | null;
  max_participants:            number | null;
  min_participants:            number | null;
  cost_per_participant:        number | null;
  currency:                    string;
  is_mandatory:                boolean;
  issues_certificate:          boolean;
  certificate_validity_months: number | null;
  material_url:                string | null;
  external_url:                string | null;
  status:                      TrainingStatus;
  enrolled_count:              number;
  created_at:                  string;
  updated_at:                  string;
}

export interface TrainingProgramCreate {
  title:                       string;
  description?:                string | null;
  category?:                   string | null;
  skills_covered?:             string[];
  trainer?:                    string | null;
  trainer_id?:                 string | null;
  mode?:                       TrainingMode;
  venue?:                      string | null;
  meeting_link?:               string | null;
  start_date?:                 string | null;
  end_date?:                   string | null;
  duration_hours?:             number | null;
  max_participants?:           number | null;
  min_participants?:           number | null;
  cost_per_participant?:       number | null;
  currency?:                   string;
  is_mandatory?:               boolean;
  issues_certificate?:         boolean;
  certificate_validity_months?: number | null;
  material_url?:               string | null;
  external_url?:               string | null;
}

export interface TrainingProgramUpdate {
  title?:                      string;
  description?:                string | null;
  category?:                   string | null;
  skills_covered?:             string[];
  trainer?:                    string | null;
  mode?:                       TrainingMode;
  venue?:                      string | null;
  meeting_link?:               string | null;
  start_date?:                 string | null;
  end_date?:                   string | null;
  duration_hours?:             number | null;
  max_participants?:           number | null;
  cost_per_participant?:       number | null;
  is_mandatory?:               boolean;
  issues_certificate?:         boolean;
  material_url?:               string | null;
  external_url?:               string | null;
  status?:                     TrainingStatus;
}

// ─── Enrollment ───────────────────────────────────────────────────────────────

export interface TrainingEnrollment {
  id:                     string;
  program_id:             string;
  employee_id:            string;
  employee?:              EmployeeMinimal | null;
  status:                 EnrollmentStatus;
  score:                  number | null;
  pass_score:             number | null;
  attendance_percentage:  number | null;
  feedback:               string | null;
  certificate_url:        string | null;
  certificate_issued_at:  string | null;
  certificate_expires_at: string | null;
  enrolled_at:            string;
  completed_at:           string | null;
  nominated_by:           string | null;
  created_at:             string;
  updated_at:             string;
}

export interface EnrollmentCreate {
  employee_ids: string[];
  nominated_by?: string | null;
}

export interface EnrollmentUpdate {
  status?:                 EnrollmentStatus;
  score?:                  number | null;
  pass_score?:             number | null;
  attendance_percentage?:  number | null;
  feedback?:               string | null;
  certificate_url?:        string | null;
  certificate_issued_at?:  string | null;
}

// ─── Lists & Filters ─────────────────────────────────────────────────────────

export interface TrainingProgramListResponse {
  count:   number;
  results: TrainingProgram[];
}

export interface TrainingFilterParams {
  status?:       TrainingStatus;
  category?:     string;
  is_mandatory?: boolean;
  search?:       string;
  page?:         number;
  page_size?:    number;
}

// ─── Stats ────────────────────────────────────────────────────────────────────

export interface TrainingStats {
  total_programs:    number;
  active_programs:   number;
  completed:         number;
  total_enrollments: number;
  completion_rate:   number;
  mandatory_pending: number;
}
