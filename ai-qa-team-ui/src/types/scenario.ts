export interface StepModel {
  step_id: string;
  category: string;
  action: string;
  expected?: string | null;
}

export interface Scenario {
  id?: string;
  scenario_id: string;
  story_id: string;
  project_id: string;

  title: string;
  description?: string;

  steps: StepModel[];

  status: string;
  created_by?: string;
  created_at?: string;

  generated_by_agent?: string;
  complexity?: string;
  approved?: boolean;
  spec_kind?: string;
  purpose?: string;
  role?: string | null;
  coverage_type?: "happy_path" | "negative" | "boundary" | "exception";
  preconditions?: string[];
  expected_outcome?: string;
  acceptance_criteria_refs?: string[];
  rule_references?: string[];
  knowledge_version_id?: string;
  story_analysis_id?: string;
}
