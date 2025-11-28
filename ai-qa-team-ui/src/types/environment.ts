export interface Credentials {
  role: string;
  username: string;
  password: string;
  notes?: string;
}

export type EnvType = "local" | "dev" | "qa" | "staging" | "prod";
export type AuthType = "none" | "basic" | "bearer";
export type BrowserType = "chromium" | "firefox" | "webkit";

export interface Environment {
  id: string;
  project_id: string;
  env_id: string;
  env_type: EnvType;
  base_url: string;
  api_base_url?: string;
  auth_type: AuthType;
  auth_token?: string;

  credentials: Credentials[];

  default_browser: BrowserType;
  default_headed: boolean;
  default_timeout_ms: number;

  variables: Record<string, any>;
}
