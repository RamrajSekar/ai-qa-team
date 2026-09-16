export type ProviderId = "managed" | "openai" | "azure_openai";

export interface ProviderField { name: string; label: string; secret: boolean; required: boolean; }
export interface ProviderDefinition { provider_id: ProviderId; label: string; modes: ("MANAGED" | "BYOK")[]; fields: ProviderField[]; capabilities: string[]; }
export interface AIConfiguration {
  project_id: string; provider_id: ProviderId; mode: "MANAGED" | "BYOK"; model?: string;
  configuration: Record<string, string>; status: string; credential_configured: boolean;
  credential_suffix?: string; validated_at?: string;
}
