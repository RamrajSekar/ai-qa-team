"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { BrainCircuit, CheckCircle2, KeyRound, PlugZap, Trash2 } from "lucide-react";
import { apiFetch } from "@/utils/api";
import { useProjects } from "@/hooks/useProjects";
import type { AIConfiguration, ProviderDefinition, ProviderId } from "@/types/ai-configuration";

export default function AIConfigurationManager({ projectId }: { projectId: string }) {
  const { projects } = useProjects();
  const canManage = projects.find((item) => item.project_id === projectId)?.current_user_role === "ADMIN";
  const [providers, setProviders] = useState<ProviderDefinition[]>([]);
  const [active, setActive] = useState<AIConfiguration | null>(null);
  const [providerId, setProviderId] = useState<ProviderId>("managed");
  const [values, setValues] = useState<Record<string, string>>({ model: "gpt-4o-mini" });
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const provider = useMemo(() => providers.find((item) => item.provider_id === providerId), [providers, providerId]);

  const load = useCallback(async () => {
    const [catalog, configuration] = await Promise.all([
      apiFetch(`/projects/${projectId}/ai/providers`), apiFetch(`/projects/${projectId}/ai/configuration`),
    ]);
    if (catalog.ok) setProviders(catalog.data);
    if (configuration.ok && configuration.data) {
      const item = configuration.data as AIConfiguration; setActive(item); setProviderId(item.provider_id);
      setValues({ model: item.model || "", ...item.configuration });
    }
  }, [projectId]);

  useEffect(() => { async function initialLoad() { await load(); } initialLoad(); }, [load]);

  function payload() {
    const configuration: Record<string, string> = {};
    for (const field of provider?.fields || []) if (!field.secret && field.name !== "model") configuration[field.name] = values[field.name] || "";
    return { provider_id: providerId, mode: providerId === "managed" ? "MANAGED" : "BYOK", model: values.model || null,
      configuration, ...(providerId !== "managed" && values.api_key ? { api_key: values.api_key } : {}) };
  }

  function detail(data: unknown, fallback: string) {
    if (!data || typeof data !== "object" || !("detail" in data)) return fallback;
    const value = (data as { detail?: unknown }).detail;
    if (typeof value === "string") return value;
    if (Array.isArray(value)) {
      const issues = value.flatMap((issue) => {
        if (!issue || typeof issue !== "object") return [];
        const record = issue as { loc?: unknown; msg?: unknown };
        if (typeof record.msg !== "string") return [];
        const location = Array.isArray(record.loc) ? record.loc.filter((part) => part !== "body").join(".") : "configuration";
        return [`${location || "configuration"}: ${record.msg}`];
      });
      return issues.length ? `Configuration error — ${issues.join("; ")}` : fallback;
    }
    if (value && typeof value === "object" && "message" in value && typeof (value as { message?: unknown }).message === "string") {
      const record = value as { code?: unknown; message: string };
      return typeof record.code === "string" ? `${record.code}: ${record.message}` : record.message;
    }
    return fallback;
  }
  async function act(path: string, method: "POST" | "PUT", success: string) {
    setBusy(true); setMessage(null);
    try {
      const response = await apiFetch(`/projects/${projectId}/ai/configuration${path}`, { method, body: JSON.stringify(payload()) });
      if (response.ok) {
        setMessage(success);
        if (method === "PUT") {
          setValues((current) => ({ ...current, api_key: "" }));
          await load();
        }
      } else setMessage(detail(response.data, "Unable to validate this provider."));
    } catch {
      setMessage("Could not reach the AI configuration service. Check your connection and try again.");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true); const response = await apiFetch(`/projects/${projectId}/ai/configuration`, { method: "DELETE" });
    if (response.ok) { setActive(null); setProviderId("managed"); setValues({ model: "gpt-4o-mini" }); setMessage("AI configuration removed."); }
    else setMessage(detail(response.data, "Unable to remove the configuration.")); setBusy(false);
  }

  return <section className="ai-config-card">
    <div className="ai-config-summary"><span><BrainCircuit size={21} /></span><div><strong>{active ? providers.find((item) => item.provider_id === active.provider_id)?.label || active.provider_id : "No active provider"}</strong><p>{active ? `${active.status} · ${active.model || active.configuration.deployment || "Configured"}` : "Choose how this project will access AI."}</p></div>{active?.credential_configured && <span className="workspace-badge"><KeyRound size={13} /> Configured{active.credential_suffix ? ` ····${active.credential_suffix}` : ""}</span>}</div>
    {!canManage ? <p className="workspace-description">A Project Admin manages AI provider settings.</p> : <div className="ai-config-form">
      <label>Provider<select value={providerId} onChange={(event) => { setProviderId(event.target.value as ProviderId); setValues(event.target.value === "managed" || event.target.value === "openai" ? { model: "gpt-4o-mini" } : { api_version: "2024-10-21" }); setMessage(null); }}>{providers.map((item) => <option value={item.provider_id} key={item.provider_id}>{item.label}</option>)}</select></label>
      <div className="ai-config-fields">{provider?.fields.map((field) => <label key={field.name}>{field.label}<input type={field.secret ? "password" : "text"} autoComplete={field.secret ? "new-password" : "off"} value={values[field.name] || ""} placeholder={field.secret && active?.credential_configured ? "Enter a new key to replace" : ""} onChange={(event) => setValues((current) => ({ ...current, [field.name]: event.target.value }))} /></label>)}</div>
      <p className="ai-config-note">{providerId === "managed"
        ? "Managed uses the platform’s OpenAI credentials configured on the backend. A platform administrator manages this key."
        : "Use your project’s provider key. Test Connection validates it; Save & Activate stores it encrypted. Existing keys are never returned."}</p>
      {message && <p className="repository-status"><CheckCircle2 size={15} />{message}</p>}
      <div className="repository-actions"><button className="workspace-button" disabled={busy} onClick={() => act("/test", "POST", "Connection successful.")}><PlugZap size={15} /> Test Connection</button><button className="workspace-button workspace-primary" disabled={busy} onClick={() => act("", "PUT", "Provider saved and activated.")}>{busy ? "Working…" : active ? "Save & Activate" : "Activate"}</button>{active && <button className="workspace-button team-remove" disabled={busy} onClick={remove}><Trash2 size={15} /> Remove</button>}</div>
    </div>}
  </section>;
}
