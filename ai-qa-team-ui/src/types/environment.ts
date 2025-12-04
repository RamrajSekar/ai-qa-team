// src/types/environment.ts

export interface EnvironmentCredentials {
  role: string;            // admin, qa, customer, etc.
  username: string;
  password: string;
  notes?: string;
}

export interface EnvironmentVariables {
  [key: string]: any;      // dynamic key/value map
}

export type AuthType = "none" | "basic" | "bearer";
export type BrowserType = "chromium" | "firefox" | "webkit";

export interface Environment {
  id: string;                 // MongoDB _id converted to string
  env_id: string;             // ENV001
  project_id: string;

  env_type: string;           // NOW TEXT FIELD (user defined naming convention)

  base_url: string;
  api_base_url?: string | null;

  auth_type: AuthType;
  auth_token?: string | null;

  credentials: EnvironmentCredentials[];
  variables: EnvironmentVariables;

  default_browser: BrowserType;
  default_headed: boolean;
  default_timeout_ms: number;
}

/**
 * Used for EnvironmentModal (create/edit)
 */
export interface EnvironmentFormState {
  env_type: string;
  base_url: string;
  api_base_url?: string;

  auth_type: AuthType;
  auth_token?: string;

  credentials: EnvironmentCredentials[];
  variables: EnvironmentVariables;

  default_browser: BrowserType;
  default_headed: boolean;
  default_timeout_ms: number;
}
