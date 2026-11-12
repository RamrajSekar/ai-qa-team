// src/types/user.ts

export interface UsageStats {
  stories_used: number;
  scenarios_used: number;
  executions_used: number;
  team_members_used: number;
  ai_gen_used: number;
  managed_ai_credits_used?: number;
  byok_ai_requests_used?: number;
  projects_used: number;
}

export interface UsageLimits {
  stories_limit: number;
  scenarios_limit: number;
  executions_limit: number;
  team_members_limit: number;
  ai_gen_limit: number;
  managed_ai_credits_limit?: number;
  byok_ai_requests_limit?: number;
  projects_limit: number;
  description?: string;
}

export interface Subscription {
  ai_allowance_version?: number | null;
  plan: string;           // "free", "pro", etc.
  start_date?: string;
  expiry_date?: string;
  status?: string;        // "active"
  provider?: string;      // "manual"
  payment_id?: string | null;
  usage?: UsageStats;
  limits?: UsageLimits;
}

export interface OnboardingInfo {
  onboarding_status: "not_started" | "in_progress" | "completed";
  current_step: number;
  steps: {
    project: boolean;
    environment: boolean;
    add_users: boolean;
    test_import: boolean;
    finish: boolean;
  };

  context: {
    project_id: string | null;
    environment_id: string | null;
  };
}

export interface User {
  account_id?: string;
  account_role?: "OWNER" | "ADMIN" | "MEMBER";
  account_state?: "ACTIVE" | "PROVISIONING";
  id?: string;
  _id?: string;
  name?: string;
  email: string;
  provider?: string;
  role?: string;
  subscription?: Subscription;
  onboarding?: OnboardingInfo;
}
