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
  attributions_created?: number;
  proposals_created?: number;
}

export interface Proposal {
  id: number;
  created_at: string;
  created_for_period: string;
  status: string;
  cost_center_id: number;
  cost_center_name: string;
  category: string;
  affected_periods: string[];
  delta_per_period: number;
  agent_rationale: string;
  driving_variance_ids: number[];
  attributed_events: AttributedEvent[];
  confidence: string;
  decided_at: string | null;
  decided_by: string | null;
  decision_note: string | null;
  modified_delta_per_period: number | null;
  resulting_forecast_version_id: number | null;
}

export interface AttributedEvent {
  attribution_type: string;
  narrative: string;
  drivers: DriverDetail[];
}

export interface DriverDetail {
  type: string;
  employee_id: number | null;
  employee_name: string | null;
  details: string;
}

export interface ProposalDetail extends Proposal {
  driving_variances: DrivingVariance[];
  attribution_records: AttributionRecordSummary[];
}

export interface DrivingVariance {
  id: number;
  cost_center_name: string;
  category: string;
  period: string;
  variance_amount: number;
  variance_pct: number;
  materiality_score: number;
  agent_severity: string | null;
  agent_rationale: string | null;
}

export interface AttributionRecordSummary {
  id: number;
  variance_id: number;
  attribution_type: string;
  narrative: string;
  structured_drivers: DriverDetail[];
  confidence: string;
}
