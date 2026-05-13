export interface HealthResponse {
  status: string;
}

export interface MonthlyDataPoint {
  period: string;
  actual: number;
  forecast: number;
}

export interface AgentAssessment {
  id: number;
  period: string;
  cost_center_id: number;
  category: string;
  severity: string | null;
  rationale: string | null;
  suggested_action: string | null;
}

export interface DashboardKPIs {
  current_month: string;
  headcount_eop: number;
  ytd_actuals: number;
  ytd_variance: number;
  fy_forecast: number;
  monthly_data: MonthlyDataPoint[];
  recent_assessments: AgentAssessment[];
}

export interface ForecastLine {
  id: number;
  version_id: number;
  cost_center_id: number;
  cost_center_name: string;
  period: string;
  category: string;
  amount: number;
  headcount_eop: number;
}

export interface VarianceRecord {
  id: number;
  cost_center_id: number;
  cost_center_name: string;
  period: string;
  category: string;
  forecast_amount: number;
  actual_amount: number;
  variance_amount: number;
  variance_pct: number;
  volume_variance: number;
  rate_variance: number;
  materiality_score: number;
  agent_severity: string | null;
  agent_unexpectedness: string | null;
  agent_rationale: string | null;
  agent_suggested_action: string | null;
}

export interface CostCenter {
  id: number;
  code: string;
  name: string;
  parent_id: number | null;
  vp_owner: string;
}

export interface AdvanceMonthResponse {
  period: string;
  story: string;
  actuals_created: number;
  events: string;
  variances_calculated: number;
  agent_assessments: number;
}
