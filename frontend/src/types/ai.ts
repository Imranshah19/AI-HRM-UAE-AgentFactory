// AI-HRMS — AI feature TypeScript types

// ─── Attrition ────────────────────────────────────────────────────────────────

export interface RiskFactor {
  factor:    string;
  label:     string;
  impact:    number;
  direction: string;
}

export interface AttritionResult {
  employee_id:         string;
  risk_score:          number;    // 0–100
  risk_tier:           'Low' | 'Medium' | 'High' | 'Critical';
  top_risk_factors:    RiskFactor[];
  recommended_actions: string[];
  confidence:          number;    // 0–1
  model_type:          string;
}

export interface HighRiskEmployee {
  id:          string;
  name:        string;
  score:       number;
  tier:        string;
  top_factor:  string;
  department?: string | null;
}

export interface AttritionOverview {
  total:                number;
  low_count:            number;
  medium_count:         number;
  high_count:           number;
  critical_count:       number;
  high_risk_employees:  HighRiskEmployee[];
  computed_at:          string | null;
}

// ─── Performance ──────────────────────────────────────────────────────────────

export interface KeyDriver {
  factor:     string;
  influence:  'positive' | 'negative' | 'neutral';
  note:       string;
  // aliases used by some UI components
  label?:     string;
  direction?: string;
}

export interface PerformancePrediction {
  employee_id:             string;
  predicted_band:          'High' | 'Medium' | 'Low';
  predicted_score:         number;    // 1–5
  confidence:              number;
  key_drivers:             KeyDriver[];
  improvement_suggestions: string[];
  predicted_at:            string;
}

// ─── Anomalies ────────────────────────────────────────────────────────────────

export type AnomalySeverity = 'low' | 'medium' | 'high';

export interface Anomaly {
  id:                 string;
  type:               string;
  severity:           AnomalySeverity;
  description:        string;
  affected_entities:  string[];
  detected_at:        string;
  recommended_action: string;
  is_reviewed:        boolean;
}

export interface AIInsights {
  anomalies:      Anomaly[];
  anomaly_count:  number;
  high_severity:  number;
  last_refreshed: string;
}

// ─── Chatbot ──────────────────────────────────────────────────────────────────

export interface SuggestedAction {
  label: string;
  url:   string;
}

export interface ChatResponse {
  answer:            string;
  data:              Record<string, unknown> | null;
  intent:            string;
  sources:           string[];
  suggested_actions: SuggestedAction[];
  confidence:        number;
}

export interface ChatMessage {
  id:        string;
  role:      'user' | 'assistant';
  content:   string;
  response?: ChatResponse;    // full response for assistant messages
  timestamp: string;
}

export interface ChatSuggestionsResponse {
  suggestions: string[];
  role:        string;
}
