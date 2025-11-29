// src/types/user.ts

export interface UsageStats {
  stories_used: number;
  scenarios_used: number;
  executions_used: number;
  team_members_used: number;
  ai_gen_used: number;
  projects_used: number;
}

export interface UsageLimits {
  stories_limit: number;
  scenarios_limit: number;
  executions_limit: number;
  team_members_limit: number;
  ai_gen_limit: number;
  projects_limit: number;
  description?: string;
}

export interface Subscription {
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
}

export interface User {
  id?: string;
  _id?: string;
  name?: string;
  email: string;
  provider?: string;
  role?: string;
  subscription?: Subscription;
  onboarding?: OnboardingInfo;
}
