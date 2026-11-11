"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/utils/api";

interface EnvironmentChoice {
  env_id?: string;
  env_type?: string;
  credentials?: { role: string; password_configured?: boolean }[];
}
interface BindingPreview {
  binding_digest: string;
  environment_id: string;
  environment_revision: number;
  target_url: string;
  application_role: string;
  credential_id: string;
  approved_test_version_id: string;
  execution_ready: false;
}
interface SavedBinding extends BindingPreview { binding_id: string }
interface BindingState { binding: SavedBinding; validation_state: "current" | "stale"; reason?: string | null }

export default function StagingBindingPanel({ projectId, testcaseId, approvedVersionId, environments }: {
  projectId: string; testcaseId: string; approvedVersionId: string; environments: EnvironmentChoice[];
}) {
  const base = `/projects/${encodeURIComponent(projectId)}/approved-visual-runs/staging-bindings`;
  const [environmentId, setEnvironmentId] = useState("");
  const [role, setRole] = useState("");
  const [preview, setPreview] = useState<BindingPreview | null>(null);
  const [saved, setSaved] = useState<BindingState | null>(null);
  const [requestKey, setRequestKey] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const environment = environments.find(item => item.env_id === environmentId);
  const roles = environment?.credentials || [];

  useEffect(() => {
    const controller = new AbortController();
    apiFetch(`${base}/testcases/${encodeURIComponent(testcaseId)}`, { signal: controller.signal, cache: "no-store" })
      .then(response => {
        if (controller.signal.aborted) return;
        if (!response.ok || (response.data !== null && !response.data?.binding?.binding_id)) {
          throw new Error("Could not load the latest staging binding.");
        }
        setSaved(response.data);
      }).catch(() => { if (!controller.signal.aborted) setError("Could not load the latest staging binding."); })
      .finally(() => { if (!controller.signal.aborted) setLoaded(true); });
    return () => controller.abort();
  }, [base, testcaseId]);

  async function request<T>(url: string, body?: object): Promise<T> {
    const response = await apiFetch(url, { method: body ? "POST" : "GET", cache: "no-store",
      signal: AbortSignal.timeout(15000), ...(body ? { body: JSON.stringify(body) } : {}) });
    if (!response.ok) throw new Error(typeof response.data?.detail === "string" ? response.data.detail : `Binding request rejected (HTTP ${response.status}).`);
    return response.data;
  }

  async function perform(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    try { await action(); }
    catch (failure) { setError(failure instanceof Error ? failure.message : "Could not prepare staging binding."); }
    finally { setBusy(false); }
  }

  const selection = { approved_test_version_id: approvedVersionId, environment_id: environmentId, application_role: role };
  return <section className="border-t pt-4 space-y-3" aria-label="Staging login preparation">
    <h3 className="font-semibold">Staging login preparation</h3>
    <p className="text-sm">Bind the saved Salesforce Sandbox environment and role to this approved version. Login actions and execution qualification follow in the next step.</p>
    <label className="block">Staging environment{" "}
      <select className="workspace-input" value={environmentId} disabled={busy} onChange={event => {
        setEnvironmentId(event.target.value); setRole(""); setPreview(null);
      }}>
        <option value="">Select an environment</option>
        {environments.filter(item => item.env_id).map(item => <option key={item.env_id} value={item.env_id}>{item.env_type || item.env_id} ({item.env_id})</option>)}
      </select>
    </label>
    <label className="block">Application role{" "}
      <select className="workspace-input" value={role} disabled={busy || !environment} onChange={event => { setRole(event.target.value); setPreview(null); }}>
        <option value="">Select a role</option>
        {roles.map(item => <option key={item.role} value={item.role}>{item.role}{item.password_configured ? "" : " — save encrypted credentials first"}</option>)}
      </select>
    </label>
    <button className="workspace-button" disabled={busy || !loaded || !environmentId || !role} onClick={() => void perform(async () => {
      const result = await request<BindingPreview>(`${base}/preview`, selection);
      setPreview(result); setRequestKey(crypto.randomUUID().replaceAll("-", ""));
    })}>Preview staging binding</button>
    {!loaded && <p role="status">Loading staging preparation…</p>}
    {preview && <div className="space-y-2">
      <p>Selected URL — {preview.target_url}</p>
      <p>Environment revision {preview.environment_revision} · Role {preview.application_role}</p>
      <p className="break-all">Approved test version {preview.approved_test_version_id}</p>
      <button className="workspace-button" disabled={busy} onClick={() => void perform(async () => {
        const binding = await request<SavedBinding>(base, { ...selection, binding_digest: preview.binding_digest, idempotency_key: requestKey });
        const status = await request<BindingState>(`${base}/${binding.binding_id}`);
        setSaved(status); setPreview(null);
      })}>Save staging binding</button>
    </div>}
    {saved && <div className="space-y-2">
      <p role="status">Staging binding {saved.validation_state} · Browser execution pending</p>
      <p>{saved.binding.target_url} · {saved.binding.application_role} · revision {saved.binding.environment_revision}</p>
      <p className="break-all">Bound approved version {saved.binding.approved_test_version_id}</p>
      {saved.reason && <p>{saved.reason}</p>}
      <button className="workspace-button" disabled={busy} onClick={() => void perform(async () => {
        setSaved(await request<BindingState>(`${base}/${saved.binding.binding_id}`));
      })}>Refresh binding validation</button>
    </div>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
