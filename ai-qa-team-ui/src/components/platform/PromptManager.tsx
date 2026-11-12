"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, RotateCcw, Save } from "lucide-react";
import { apiFetch } from "@/utils/api";
import { WorkspaceDialog } from "@/components/ui/workspace-dialog";
import type { PromptDefinition, PromptVersion } from "@/types/platform-admin";

export default function PromptManager({ promptKey }: { promptKey: string }) {
  const [definition, setDefinition] = useState<PromptDefinition | null>(null);
  const [versions, setVersions] = useState<PromptVersion[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [draftText, setDraftText] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [activation, setActivation] = useState<number | null>(null);
  const selected = useMemo(() => versions.find((item) => item.version === selectedVersion), [versions, selectedVersion]);

  const load = useCallback(async () => {
    const [detail, history] = await Promise.all([
      apiFetch(`/platform-admin/prompts/${promptKey}`), apiFetch(`/platform-admin/prompts/${promptKey}/versions`),
    ]);
    if (!detail.ok || !history.ok) throw new Error("Could not load this platform prompt. Check your access and try again.");
    setDefinition(detail.data); setVersions(history.data);
  }, [promptKey]);

  useEffect(() => { let current = true; void load().catch(() => { if (current) setError("Could not load this platform prompt. Check your access and try again."); }); return () => { current = false; }; }, [load]);
  function chooseVersion(version: PromptVersion | null) {
    setSelectedVersion(version?.version ?? null);
    setDraftText(version?.system_prompt ?? "");
  }

  function errorText(data: unknown) {
    if (data && typeof data === "object" && "detail" in data) {
      const detail = (data as { detail?: unknown }).detail;
      if (typeof detail === "string") return detail;
    }
    return "Unable to update this prompt.";
  }

  async function change(work: () => Promise<void>) {
    setBusy(true); setError(""); setMessage(null);
    try { await work(); } catch (failure) { setError(failure instanceof Error ? failure.message : "Could not reach the prompt service."); }
    finally { setBusy(false); }
  }
  async function post(path: string, method: string, body?: object) {
    const response = await apiFetch(`/platform-admin/prompts/${promptKey}/${path}`, { method, ...(body ? { body: JSON.stringify(body) } : {}) });
    if (!response.ok) throw new Error(errorText(response.data));
    return response.data;
  }
  async function createDraft() {
    if (!definition) return;
    const draft = await post("versions", "POST", { base_version: selected?.version ?? definition.active.resolved_version });
    await load(); chooseVersion(draft); setMessage(`Draft v${draft.version} created.`);
  }
  async function saveDraft() {
    if (!selected) return;
    await post(`versions/${selected.version}`, "PATCH", { system_prompt: draftText });
    await load(); setMessage(`Draft v${selected.version} saved.`);
  }
  async function activate(version: number) {
    await post(`versions/${version}/activate`, "POST");
    await load(); setSelectedVersion(version); setActivation(null); setMessage(`Version ${version} is active for future requests.`);
  }
  if (!definition) return <section className="workspace-panel"><div className="workspace-empty">
    {error ? <><p role="alert">{error}</p><button className="workspace-button" onClick={() => void change(load)}>Try again</button></> : <p role="status">Loading prompt…</p>}
  </div></section>;
  const dirty = selected?.status === "DRAFT" && draftText !== selected.system_prompt;
  const displayedText = selected ? draftText : definition.active.system_prompt;
  const displayedStatus = selected?.status || (definition.active.source === "CODE_FALLBACK" ? "CODE DEFAULT" : "ACTIVE");

  return <div><div className="workspace-page-header"><div><p className="workspace-eyebrow">Platform prompt</p><h1>{definition.name}</h1><p className="workspace-description">{definition.description}</p></div><button className="workspace-button workspace-primary" disabled={busy} onClick={() => void change(createDraft)}>Create Draft</button></div>
    <p className="workspace-notice">Platform administrators manage task instructions here. Project knowledge stays project-scoped and is supplied separately. Prompt changes do not train the model or change approved knowledge. Schemas, permissions and approval rules remain enforced by the backend. Activation affects future requests; copy a published version into a draft to edit it.</p>
    <WorkspaceDialog open={activation !== null} onClose={() => setActivation(null)} title="Activate platform prompt" busy={busy}>
      <h2>Activate version {activation}?</h2><p className="workspace-description">Future requests across projects will use this instruction version. Existing approved knowledge and test designs stay unchanged.</p>
      {error && <p role="alert">{error}</p>}<div className="repository-actions"><button className="workspace-button" disabled={busy} onClick={() => setActivation(null)}>Cancel</button><button className="workspace-button workspace-primary" disabled={busy} onClick={() => activation !== null && void change(() => activate(activation))}>Confirm activation</button></div>
    </WorkspaceDialog>
    <div className="prompt-layout"><section className="workspace-panel prompt-editor"><div className="workspace-panel-header"><h2>{selected ? `Version ${selected.version}` : "Active Prompt"}</h2><div className="prompt-row-meta"><span className="workspace-badge">{displayedStatus}</span><span className="workspace-badge">{definition.output_contract}</span></div></div><div className="prompt-editor-body"><dl className="prompt-metadata"><div><dt>Prompt Key</dt><dd>{definition.prompt_key}</dd></div><div><dt>Active Source</dt><dd>{definition.active.source === "CODE_FALLBACK" ? "Code Default" : "Database"}</dd></div><div><dt>Active Version</dt><dd>{definition.active.resolved_version}</dd></div></dl>{Boolean(definition.template_variables?.length) && <p className="workspace-notice">Keep these placeholders: {definition.template_variables?.map(name => `{{${name}}}`).join(", ")}. Customer values are inserted only when the task runs.</p>}<textarea aria-label="System prompt" rows={20} readOnly={selected?.status !== "DRAFT"} value={displayedText} onChange={(event) => setDraftText(event.target.value)} />{error && <p role="alert" className="repository-error">{error}</p>}{dirty && <p className="workspace-notice">Unsaved changes. Save the draft before activating it.</p>}{message && <p role="status" className="repository-status"><CheckCircle2 size={15} />{message}</p>}{selected?.status === "DRAFT" && <div className="repository-actions"><button className="workspace-button" disabled={busy} onClick={() => void change(saveDraft)}><Save size={15} />Save Draft</button><button className="workspace-button workspace-primary" disabled={busy || dirty} onClick={() => setActivation(selected.version)}>Activate</button></div>}{selected?.status === "INACTIVE" && <div className="repository-actions"><button className="workspace-button" disabled={busy || dirty} onClick={() => setActivation(selected.version)}><RotateCcw size={15} />Activate Version</button></div>}</div></section>
      <aside className="workspace-panel prompt-history"><div className="workspace-panel-header"><h2>Version History</h2></div><div className="workspace-panel-body"><button className="workspace-row" onClick={() => chooseVersion(null)}><div><p className="workspace-row-title">Current resolution</p><p className="workspace-row-subtitle">{definition.active.resolved_version}</p></div><span className="workspace-badge">{definition.active.source === "CODE_FALLBACK" ? "Code Default" : "Active"}</span></button>{versions.map((version) => <button className="workspace-row" key={version.version} onClick={() => chooseVersion(version)}><div><p className="workspace-row-title">Version {version.version}</p><p className="workspace-row-subtitle">{version.created_by} · {new Date(version.created_at).toLocaleString()}</p></div><span className="workspace-badge">{version.status}</span></button>)}</div></aside></div>
  </div>;
}
