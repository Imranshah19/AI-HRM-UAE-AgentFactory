// AI-HRMS — Recruitment / ATS TypeScript types

// ─── Enums ────────────────────────────────────────────────────────────────────

export type JobStatus       = 'draft' | 'open' | 'closed' | 'on_hold' | 'filled';
export type EmploymentType  = 'full_time' | 'part_time' | 'contract' | 'internship' | 'remote';
export type ApplicationStatus =
  | 'applied' | 'screening' | 'shortlisted' | 'interview'
  | 'offered' | 'hired' | 'rejected' | 'withdrawn';
export type ApplicationSource =
  | 'portal' | 'linkedin' | 'indeed' | 'referral' | 'direct' | 'agency' | 'campus' | 'other';
export type InterviewMode           = 'online' | 'in_person' | 'phone';
export type InterviewStatus         = 'scheduled' | 'completed' | 'cancelled' | 'no_show' | 'rescheduled';
export type InterviewRecommendation = 'proceed' | 'reject' | 'hold';

// ─── Nested ───────────────────────────────────────────────────────────────────

export interface DepartmentMinimal {
  id:   string;
  name: string;
}

export interface DesignationMinimal {
  id:    string;
  title: string;
}

export interface EmployeeMinimal {
  id:            string;
  employee_code: string;
  full_name:     string;
  photo_url:     string | null;
}

// ─── Job Posting ──────────────────────────────────────────────────────────────

export interface StageCounts {
  applied:     number;
  screening:   number;
  shortlisted: number;
  interview:   number;
  offered:     number;
  hired:       number;
  rejected:    number;
  withdrawn:   number;
}

export interface JobPosting {
  id:                   string;
  title:                string;
  location:             string | null;
  description:          string | null;
  requirements:         string[];
  responsibilities:     string[];
  benefits:             string | null;
  vacancies:            number;
  employment_type:      EmploymentType;
  experience_years_min: number;
  experience_years_max: number | null;
  salary_min:           number | null;
  salary_max:           number | null;
  is_salary_visible:    boolean;
  required_skills:      string[];
  status:               JobStatus;
  is_internal:          boolean;
  posted_at:            string | null;
  closing_date:         string | null;
  department:           DepartmentMinimal | null;
  designation:          DesignationMinimal | null;
  application_count:    number;
  stage_counts:         StageCounts;
  created_at:           string;
  updated_at:           string;
}

export interface JobPostingListItem {
  id:               string;
  title:            string;
  location:         string | null;
  employment_type:  EmploymentType;
  vacancies:        number;
  status:           JobStatus;
  closing_date:     string | null;
  department_name:  string | null;
  application_count: number;
  created_at:       string;
}

export interface JobPostingCreate {
  title:                string;
  department_id:        string | null;
  designation_id:       string | null;
  location:             string | null;
  description:          string | null;
  requirements:         string[];
  responsibilities:     string[];
  benefits:             string | null;
  vacancies:            number;
  employment_type:      EmploymentType;
  experience_years_min: number;
  experience_years_max: number | null;
  salary_range_min:     number | null;
  salary_range_max:     number | null;
  salary_visible:       boolean;
  is_salary_visible?:   boolean;   // alias
  skills_required:      string[];
  closing_date:         string | null;
  is_internal:          boolean;
}

export type JobPostingUpdate = Partial<JobPostingCreate>;

export interface JobPostingListResponse {
  count:   number;
  results: JobPostingListItem[];
}

// Alias — some pages import JobPostingResponse (the full detail shape)
export type JobPostingResponse = JobPosting;

// ─── Application ──────────────────────────────────────────────────────────────

export interface StageHistoryItem {
  from_status: string | null;
  to_status:   string;
  changed_by:  string | null;
  notes:       string | null;
  changed_at:  string;
}

export interface JobApplication {
  id:                string;
  job_posting_id:    string;
  job_posting:       JobPostingListItem | null;
  candidate_name:    string;
  candidate_email:   string;
  candidate_phone:   string | null;
  candidate_location: string | null;
  cv_url:            string | null;
  cover_letter:      string | null;
  portfolio_url:     string | null;
  linkedin_url:      string | null;
  source:            ApplicationSource;
  referred_by:       string | null;
  applied_at:        string;
  status:            ApplicationStatus;
  rejection_reason:  string | null;
  is_archived:       boolean;
  ai_score:          number | null;
  ai_explanation:    Record<string, any> | null;
  ai_scored_at:      string | null;
  hr_notes:          string | null;
  offer_letter_url:  string | null;
  offer_sent_at:     string | null;
  offer_deadline:    string | null;
  hired_employee_id: string | null;
  stage_history:     StageHistoryItem[];
  interviews:        Interview[];
  created_at:        string;
  updated_at:        string;
}

export interface JobApplicationListItem {
  id:              string;
  job_posting_id:  string;
  job_title:       string | null;
  candidate_name:  string;
  candidate_email: string;
  source:          ApplicationSource;
  status:          ApplicationStatus;
  ai_score:        number | null;
  applied_at:      string;
  created_at:      string;
}

export interface ApplicationListResponse {
  count:   number;
  results: JobApplicationListItem[];
}

export interface JobApplicationCreate {
  job_posting_id:          string;
  candidate_name:          string;
  candidate_email:         string;
  candidate_phone?:        string;
  candidate_location?:     string;
  cv_url?:                 string;
  cover_letter?:           string;
  portfolio_url?:          string;
  linkedin_url?:           string;
  source:                  ApplicationSource;
  referred_by_employee_id?: string;
  expected_salary?:        number;
  notice_period_days?:     number;
}

export interface ApplicationStageUpdate {
  new_status:       ApplicationStatus;
  notes?:           string;
  rejection_reason?: string;
}

export interface ApplicationFilterParams {
  job_posting_id?: string;
  status?:         ApplicationStatus;
  source?:         ApplicationSource;
  date_from?:      string;
  date_to?:        string;
  min_ai_score?:   number;
  search?:         string;
  page?:           number;
  page_size?:      number;
}

// ─── AI Scoring ───────────────────────────────────────────────────────────────

export interface ScoringResult {
  score:            number;
  skills_matched:   string[];
  skills_missing:   string[];
  skills_score:     number;
  experience_score: number;
  title_relevance:  number;
  education_score:  number;
  explanation:      string;
  bias_flags:       string[];
  scored_at:        string;
}

// ─── Interview ────────────────────────────────────────────────────────────────

export interface Interview {
  id:               string;
  application_id:   string;
  round_number:     number;
  title:            string | null;
  interviewer_id:   string | null;
  interviewer:      EmployeeMinimal | null;
  scheduled_at:     string | null;
  duration_minutes: number;
  mode:             InterviewMode;
  meeting_link:     string | null;
  location:         string | null;
  status:           InterviewStatus;
  feedback:         string | null;
  rating:           number | null;
  recommendation:   InterviewRecommendation | null;
  completed_at:     string | null;
  created_at:       string;
}

export interface InterviewScheduleRequest {
  application_id:       string;
  interviewer_ids:      string[];
  scheduled_at:         string;
  duration_minutes:     number;
  mode:                 InterviewMode;
  location_or_link?:    string;
  notes_for_candidate?: string;
  title?:               string;
}

export interface InterviewFeedbackRequest {
  rating:         number;
  feedback:       string;
  recommendation: InterviewRecommendation;
}

// ─── Offer Letter ─────────────────────────────────────────────────────────────

export interface OfferLetterRequest {
  application_id:    string;
  offered_salary:    number;
  joining_date:      string;
  offer_expiry_date: string;
  additional_terms?: string;
}

// ─── Pipeline / Kanban ────────────────────────────────────────────────────────

export interface PipelineColumnData {
  status:       ApplicationStatus;
  count:        number;
  applications: JobApplicationListItem[];
}

export interface PipelineStats {
  job_posting_id: string;
  job_title:      string;
  total:          number;
  columns:        PipelineColumnData[];
}

// ─── CV Upload ────────────────────────────────────────────────────────────────

export interface CVUploadResponse {
  cv_url:    string;
  filename:  string;
  file_size: number;
}
