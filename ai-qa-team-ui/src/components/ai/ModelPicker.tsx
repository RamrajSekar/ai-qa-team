"use client";
import { useState } from "react";
import type { ProviderId } from "@/types/ai-configuration";

// Suggestions only. Availability and schema support depend on the customer's account.
const models: Partial<Record<ProviderId, { id: string; label: string }[]>> = {
  managed: [{ id: "gpt-4o-mini", label: "GPT-4o mini (existing default)" }],
  openai: [{ id: "gpt-4.1-mini", label: "GPT-4.1 mini (legacy)" }, { id: "gpt-4o-mini", label: "GPT-4o mini (legacy)" }],
  gemini: [{ id: "gemini-3.8-flash", label: "Gemini 3.8 Flash" }, { id: "gemini-4-hydrogen", label: "Gemini 4 Hydrogen" }],
  anthropic: [{ id: "claude-sonnet-5-5", label: "Claude Sonnet 5.5" }, { id: "claude-haiku-5-5", label: "Claude Haiku 5.5" }],
};

export default function ModelPicker({ providerId, value, onChange }: { providerId: ProviderId; value: string; onChange: (value: string) => void }) {
  const options = models[providerId] || [];
  const [custom, setCustom] = useState(false);
  const isCustom = custom || (!!value && !options.some(item => item.id === value));
  return <div>
    <label>Model<select aria-label="Model" value={isCustom ? "__other" : value} onChange={event => {
      const other = event.target.value === "__other";
      setCustom(other);
      onChange(other ? "" : event.target.value);
    }}>
      <option value="" disabled>Choose a model</option>
      {options.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
      <option value="__other">Other model</option>
    </select></label>
    {isCustom && <label>Custom model<input autoComplete="off" value={value} onChange={event => onChange(event.target.value)} /></label>}
    <p className="ai-config-note">Test Connection checks access. Model support and availability may vary.</p>
  </div>;
}
