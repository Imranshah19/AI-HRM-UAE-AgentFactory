// AI-HRMS — Performance Management TypeScript types

// ─── Enums ────────────────────────────────────────────────────────────────────

export type CycleStatus =
  | 'upcoming' | 'active' | 'self_review' | 'manager_review'
  | 'calibration' | 'completed' | 'archived';

export type AppraisalStatus =
  | 'not_started' | 'self_review_pending' | 'self_review_submitted'
  | 'manager_review_pending' | 'manager_review_submitted'
  | 'hr_review' | 'completed';

export type GoalStatus = 'active' | 'completed' | 'missed' | 'cancelled' | 'on_hold';
export type GoalCategory = 'performance' | 'learning' | 'behavioral' | 'project' | 'other';
export type RatingScale = '1_to_5' | '1_to_10' | 'A_to_E' | 'custom';
export type ReviewType = 'self' | 'manager' | 'peer' | 'subordinate';
export type PIPStatus  = 'active' | 'completed' | 'cancelled';

// ─── Cycle ────────────────────────────────────────────────────────────────────

export interface AppraisalCycle {
  id:                          string;
  name:                        string;
  year:                        number;
  quarter:                     number | null;
  period_label:                string | null;
  start_date:                  string;
  end_date:                    string;
  self_review_deadline:        string | null;
  manager_review_deadline:     string | null;
  status:                      CycleStatus;
  rating_scale_min:            number;
  rating_scale_max:            number;
  self_review_instructions:    string | null;
  manager_review_instructions: string | null;
  // computed
  total_employees?:            number;
  reviews_completed?:          number;
  created_at:                  string;
  updated_at:                  string;
}

export interface AppraisalCycleCreate {
  name:                        string;
  year:                        number;
  quarter?:                    number | null;
  period_label?:               string | null;
  start_date:                  string;
  end_date:                    string;
  self_review_deadline?:       string | null;
  manager_review_deadline?:    string | null;
  rating_scale_min?:           number;
  rating_scale_max?:           number;
  self_review_instructions?:   string | null;
  manager_review_instructions?: string | null;
}

// ─── Goal ─────────────────────────────────────────────────────────────────────

export interface Goal {
  id:                string;
  employee_id:       string;
  cycle_id:          string | null;
  title:             string;
  description:       string | null;
  category:          GoalCategory;
  target:            string | null;
  target_value:      number | null;
  achievement:       string | null;
  achievement_value: number | null;
  weight:            number;
  due_date:          string | null;
  status:            GoalStatus;
  set_by:            'manager' | 'self' | null;
  created_at:        string;
  updated_at:        string;
}

export interface GoalCreate {
  employee_id:   string;
  cycle_id?:     string | null;
  title:         string;
  description?:  string | null;
  category?:     GoalCategory;
  target?:       string | null;
  target_value?: number | null;
  weight:        number;
  due_date?:     string | null;
}

export interface GoalUpdate {
  achievement?:       string | null;
  achievement_value?: number | null;
  status?:            GoalStatus;
  title?:             string;
  description?:       string | null;
  weight?:            number;
}

export interface GoalsBulkSet {
  employee_id: string;
  cycle_id:    string;
  goals:       GoalCreate[];
}

// ─── Competency scores ────────────────────────────────────────────────────────

export type CompetencyKey =
  | 'communication' | 'teamwork' | 'leadership'
  | 'problem_solving' | 'initiative';

export type CompetencyScores = Record<CompetencyKey, number>;

// ─── KPI score entry in JSONB ─────────────────────────────────────────────────

export interface KPIScoreEntry {
  goal_id:    string;
  goal_title: string;
  weight:     number;
  self_score: number | null;
  mgr_score:  number | null;
}

// ─── Appraisal ────────────────────────────────────────────────────────────────

export interface EmployeeMinimal {
  id:            string;
  employee_code: string;
  full_name:     string;
  photo_url:     string | null;
  department?:   string | null;
  designation?:  string | null;
}

export interface Appraisal {
  id:                      string;
  cycle_id:                string;
  cycle?:                  Pick<AppraisalCycle, 'id' | 'name' | 'year' | 'quarter' | 'status'>;
  employee_id:             string;
  employee?:               EmployeeMinimal;
  reviewer_id:             string | null;
  reviewer?:               EmployeeMinimal | null;
  self_rating:             number | null;
  manager_rating:          number | null;
  final_rating:            number | null;
  kpi_scores:              KPIScoreEntry[] | null;
  // Qualitative
  self_strengths:          string | null;
  self_improvements:       string | null;
  self_achievements:       string | null;
  manager_feedback:        string | null;
  hr_comments:             string | null;
  // Recommendations
  increment_recommended:   boolean;
  increment_percentage:    number | null;
  promotion_recommended:   boolean;
  promotion_to_designation: string | null;
  // Status & timestamps
  status:                  AppraisalStatus;
  self_submitted_at:       string | null;
  manager_submitted_at:    string | null;
  finalized_at:            string | null;
  employee_acknowledged:   boolean;
  acknowledged_at:         string | null;
  created_at:              string;
  updated_at:              string;
}

// ─── Review submissions ───────────────────────────────────────────────────────

export interface SelfReviewSubmit {
  kpi_scores:              Record<string, number>;   // goal_id → score
  competency_scores:       CompetencyScores;
  self_achievements:       string;
  self_improvements:       string;
  self_strengths:          string;
}

export interface ManagerReviewSubmit {
  kpi_scores:               Record<string, number>;
  competency_scores:        CompetencyScores;
  manager_feedback:         string;
  final_rating:             number;
  increment_recommended:    boolean;
  increment_percentage?:    number | null;
  promotion_recommended:    boolean;
  promotion_to_designation?: string | null;
  pip_recommended:          boolean;
  // If pip_recommended → inline PIP fields
  pip_improvement_areas?:   string[];
  pip_action_items?:        PIPActionItem[];
  pip_review_date?:         string | null;
}

// ─── PIP ─────────────────────────────────────────────────────────────────────

export interface PIPActionItem {
  action:   string;
  deadline: string;
  metric:   string;
}

export interface PIP {
  id:                string;
  employee_id:       string;
  employee?:         EmployeeMinimal;
  cycle_id:          string | null;
  improvement_areas: string[];
  action_items:      PIPActionItem[];
  review_date:       string;
  supervisor_id:     string | null;
  supervisor?:       EmployeeMinimal | null;
  status:            PIPStatus;
  notes:             string | null;
  created_at:        string;
  updated_at:        string;
}

export interface PIPCreate {
  employee_id:       string;
  cycle_id?:         string | null;
  improvement_areas: string[];
  action_items:      PIPActionItem[];
  review_date:       string;
  supervisor_id?:    string | null;
  notes?:            string | null;
}

// ─── Bell curve ───────────────────────────────────────────────────────────────

export interface BellCurveBucket {
  rating:       number;
  label:        string;
  count:        number;
  percentage:   number;
  employees:    EmployeeMinimal[];
}

export interface BellCurveData {
  cycle_id:    string;
  total:       number;
  buckets:     BellCurveBucket[];
  is_skewed:   boolean;
  skew_note:   string | null;
}

// ─── Team summary ─────────────────────────────────────────────────────────────

export interface TeamMemberSummary {
  employee:             EmployeeMinimal;
  appraisal_id:         string | null;
  status:               AppraisalStatus | null;
  self_rating:          number | null;
  manager_rating:       number | null;
  final_rating:         number | null;
  self_submitted_at:    string | null;
  manager_submitted_at: string | null;
}

export interface TeamPerformanceSummary {
  cycle_id:    string;
  cycle_name:  string;
  members:     TeamMemberSummary[];
  avg_rating:  number | null;
  top_count:   number;    // final_rating >= 4
  pip_count:   number;
}

// ─── Filters ─────────────────────────────────────────────────────────────────

export interface AppraisalFilterParams {
  cycle_id?:    string;
  employee_id?: string;
  status?:      AppraisalStatus;
  page?:        number;
  page_size?:   number;
}

export interface AppraisalListResponse {
  count:   number;
  results: Appraisal[];
}

export interface AppraisalCycleListResponse {
  count:   number;
  results: AppraisalCycle[];
}

export interface CycleListResponse {
  count:   number;
  results: AppraisalCycle[];
}

export interface PIPUpdate {
  status?:       PIPStatus;
  notes?:        string | null;
  action_items?: PIPActionItem[];
  review_date?:  string | null;
}
