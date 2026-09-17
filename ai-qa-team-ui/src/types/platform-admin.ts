export type PlatformRole = "OWNER" | "ADMIN" | "NONE";
export type PromptStatus = "DRAFT" | "ACTIVE" | "INACTIVE";

export interface PromptVersion {
  version: number; system_prompt: string; status: PromptStatus;
  created_by: string; created_at: string; activated_at?: string | null;
}

export interface ResolvedPrompt {
  prompt_key: string; resolved_version: number | "CODE_DEFAULT_V1";
  source: "DATABASE" | "CODE_FALLBACK"; system_prompt: string;
}

export interface PromptDefinition {
  prompt_key: string; name: string; description: string; output_contract: string;
  active_version?: number | null; active: ResolvedPrompt;
}
