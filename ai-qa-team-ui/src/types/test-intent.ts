export type Confidence = "HIGH" | "MEDIUM" | "LOW";
export type InputConstraintType = "EXACT" | "CONSTRAINED" | "UNSPECIFIED";

export interface IntentConstraint {
  type: string;
  value?: string | number | string[] | null;
  start?: string | number | null;
  end?: string | number | null;
  unit?: string | null;
  description?: string | null;
}

export interface WorkflowStep {
  step_number: number;
  action: string;
  target?: string | null;
  details: string;
  raw_text: string;
}

export interface IntentInput {
  name: string;
  raw_value?: string | null;
  constraint_type: InputConstraintType;
  constraint?: IntentConstraint | null;
  confidence?: Confidence | null;
}

export interface TestIntentV1 {
  source: "PASTED_BUG";
  schema_version: "1";
  title: string;
  description: string;
  environment?: string | null;
  preconditions: string[];
  workflow_steps: WorkflowStep[];
  inputs: IntentInput[];
  expected_result?: string | null;
  actual_result?: string | null;
  reported_behavior?: string | null;
  ambiguities: Array<{ field: string; description: string; severity: "INFO" | "WARNING" }>;
  confidence: Confidence;
}

export interface BugInterpretResponse {
  test_intent: TestIntentV1;
  interpretation_metadata: {
    prompt_key: string;
    prompt_version: number | string;
    prompt_source: string;
    schema_version: "1";
  };
}
