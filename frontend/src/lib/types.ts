export type RiskLevel = "low" | "medium" | "high";
export type Severity = "critical" | "warning" | "info";

export interface SummaryOut {
  total_lines: number;
  code_lines: number;
  blank_lines: number;
  comment_lines: number;
  functions: number;
  classes: number;
  average_function_length: number;
  max_function_length: number;
  max_nesting_depth: number;
  max_complexity: number;
  avg_complexity: number;
  total_cognitive: number;
  overall_health: number;
  code_health: number;
  grade: string;
  maintainability_score: number;
  risk_score: number;
  average_health: number;
  worst_health: number;
  findings_total: number;
  critical: number;
  warning: number;
  info: number;
  imports: string[];
  worst_function: string | null;
  verdict: string;
  defect_risk_high?: number;
  defect_risk_max?: number;
  riskiest_function?: string;
}

export interface FactorCell {
  score: number;
  findings: number;
}

export interface FactorMeta {
  key: string;
  label: string;
  weight: number;
  category: string;
  description: string;
  what: string;
  measures: string;
  how: string;
  score: number;
  findings: number;
}

export interface FunctionOut {
  name: string;
  line_start: number;
  line_end: number;
  lines: number;
  complexity: number;
  cognitive: number;
  nesting_depth: number;
  parameters: number;
  param_names: string[];
  elif_chain: number;
  has_docstring: boolean;
  health_score: number;
  risk: RiskLevel;
  factors: Record<string, FactorCell>;
  calls: string[];
  called_by: string[];
  responsibilities: { name: string; lines: number[] }[];
  findings: { critical: number; warning: number; info: number };
  purpose: string;
  explanation: { why: string; evidence: string[]; recommendation: string };
  defect_risk?: DefectRisk;
}

export interface DefectRisk {
  probability: number;
  band: RiskLevel;
  drivers: { name: string; effect: number; direction: "raises" | "lowers" }[];
}

export interface IssueOut {
  id: string;
  factor: string;
  rule: string;
  severity: Severity;
  title: string;
  function: string;
  line_start: number;
  line_end: number;
  lines: number[];
  evidence: string;
  metric_label: string;
  metric_value: string;
  why: string;
  recommendation: string;
  auto_fix: string | null;
  health_score: number;
}

export interface GraphNodeOut {
  id: string;
  name: string;
  health_score: number;
  complexity: number;
  lines: number;
  risk: RiskLevel;
  issues: number;
}

export interface GraphOut {
  nodes: GraphNodeOut[];
  edges: { source: string; target: string }[];
}

export interface RefactorSnapshot {
  overall_health: number;
  grade: string;
  functions: number;
  max_complexity: number;
  max_nesting_depth: number;
  avg_complexity: number;
  max_function_length: number;
  findings_total: number;
  critical: number;
  warning: number;
  info: number;
  maintainability_score: number;
  factors: Record<string, number>;
}

export interface RefactorOut {
  available: boolean;
  reason?: string;
  original?: string;
  refactored?: string;
  steps?: { kind: string; title: string; detail: string; function: string; lines: number[] }[];
  functions?: string[];
  compiles?: boolean;
  before?: RefactorSnapshot;
  after?: RefactorSnapshot;
  after_issues?: { function: string; title: string; severity: Severity }[];
  still_manual?: string[];
  note?: string;
}

export interface ExplanationOut {
  source: "claude" | "fallback";
  model: string | null;
  summary: string;
  why: string;
  recommendation: string;
  purpose: string;
  priorities: { id: string; title: string; function: string; reason: string }[];
  overview: { entry_points: string[]; leaf_functions: string[]; activities: string[]; description: string };
}

export interface AnalyzeResponse {
  filename: string;
  summary: SummaryOut;
  factors: FactorMeta[];
  categories: Record<string, number>;
  functions: FunctionOut[];
  issues: IssueOut[];
  graph: GraphOut;
  refactor: RefactorOut | null;
  explanation: ExplanationOut;
  engine_status: Record<string, string | null>;
  ml?: ModelCard | null;
  history_id?: number;
}

export interface HistoryEntry {
  id: string;
  filename: string;
  date: string;
  health: number;
  risk_score: number;
  functions: number;
  status: RiskLevel;
  result: AnalyzeResponse;
  code: string;
}

export interface ModelCard {
  name: string;
  trained_at: string;
  protocol: string;
  functions: number;
  defective: number;
  repos: number;
  auc: number;
  auc_std: number;
  recall_at_20: number;
  baseline_lines_auc: number;
}

export interface ModelDetail extends ModelCard {
  base_rate: number;
  per_repo: Record<string, { functions: number; defective: number }>;
  comparison: Record<string, { auc: number; auc_std: number; average_precision: number; precision_at_20: number; recall_at_20: number }>;
  coefficients: { feature: string; weight: number }[];
  hand_weights: Record<string, number>;
  learned_weights: Record<string, number>;
  label_definition: string;
  caveats: string[];
}

export interface RunRow {
  id: number;
  project_id: number | null;
  parent_id: number | null;
  kind: "file" | "zip" | "github";
  label: string;
  overall_health: number;
  grade: string;
  files: number;
  functions: number;
  findings: number;
  critical: number;
  high_risk_functions: number;
  max_defect_risk: number;
  created_at: string;
}

export interface ProjectRow {
  id: number;
  name: string;
  description: string;
  created_at: string;
  runs: number;
  latest_health: number | null;
  latest_grade: string | null;
  trend: { at: string; health: number; label: string }[];
}

export interface RepoReport {
  id: number;
  kind: string;
  label: string;
  project: {
    overall_health: number; grade: string; files: number; functions: number; code_lines: number; findings: number;
    critical: number; warning: number; info: number; high_risk_functions: number; factor_scores: Record<string, number>;
    riskiest_functions: { name: string; file: string; health: number; line: number; risk: number; band: RiskLevel }[];
    worst_files: { file: string; health: number; grade: string }[];
  };
  files: { id: number; filename: string; health: number; grade: string; functions: number; findings: number; critical: number; high_risk: number; max_risk: number }[];
  notes: string[];
  errors: { file: string; message: string; line: number | null }[];
}
