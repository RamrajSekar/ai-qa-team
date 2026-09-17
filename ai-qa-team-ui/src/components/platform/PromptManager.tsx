"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, RotateCcw, Save } from "lucide-react";
import { apiFetch } from "@/utils/api";
import type { PromptDefinition, PromptVersion } from "@/types/platform-admin";

export default function PromptManager({ promptKey }: { promptKey: string }) {
  const [definition, setDefinition] = useState<PromptDefinition | null>(null);
  const [versions, setVersions] = useState<PromptVersion[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [draftText, setDraftText] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const selected = useMemo(() => versions.find((item) => item.version === selectedVersion), [versions, selectedVersion]);

  const load = useCallback(async () => {
    const [detail, history] = await Promise.all([
      apiFetch(`/platform-admin/prompts/${promptKey}`), apiFetch(`/platform-admin/prompts/${promptKey}/versions`),
    ]);
    if (detail.ok) setDefinition(detail.data);
    if (history.ok) setVersions(history.data);
  }, [promptKey]);

  useEffect(() => { async function initialLoad() { await load(); } initialLoad(); }, [load]);
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

  async function createDraft() {
    if (!definition) return; setBusy(true); setMessage(null);
    const response = await apiFetch(`/platform-admin/prompts/${promptKey}/versions`, {
      method: "POST", body: JSON.stringify({ base_version: definition.active.resolved_version }),
    });
    if (response.ok) { await load(); chooseVersion(response.data as PromptVersion); setMessage(`Draft v${response.data.version} created.`); }
    else setMessage(errorText(response.data)); setBusy(false);
  }

  async function saveDraft() {
    if (!selected) return; setBusy(true); setMessage(null);
    const response = await apiFetch(`/platform-admin/prompts/${promptKey}/versions/${selected.version}`, {
      method: "PATCH", body: JSON.stringify({ system_prompt: draftText }),
    });
    if (response.ok) { await load(); setMessage(`Draft v${selected.version} saved.`); }
    else setMessage(errorText(response.data)); setBusy(false);
  }

  async function activate(version: number) {
    if (!window.confirm(`Activate prompt version ${version}?`)) return;
    setBusy(true); setMessage(null);
    const response = await apiFetch(`/platform-admin/prompts/${promptKey}/versions/${version}/activate`, { method: "POST" });
    if (response.ok) { await load(); setSelectedVersion(version); setMessage(`Version ${version} is active.`); }
    else setMessage(errorText(response.data)); setBusy(false);
  }

  if (!definition) return <p className="workspace-description">Loading prompt…</p>;
  const displayedText = selected ? draftText : definition.active.system_prompt;
  const displayedStatus = selected?.status || (definition.active.source === "CODE_FALLBACK" ? "CODE DEFAULT" : "ACTIVE");

  return <div><div className="workspace-page-header"><div><p className="workspace-eyebrow">Platform prompt</p><h1>{definition.name}</h1><p className="workspace-description">{definition.description}</p></div><button className="workspace-button workspace-primary" disabled={busy} onClick={createDraft}>Create Draft</button></div>
    <div className="prompt-layout"><section className="workspace-panel prompt-editor"><div className="workspace-panel-header"><h2>{selected ? `Version ${selected.version}` : "Active Prompt"}</h2><div className="prompt-row-meta"><span className="workspace-badge">{displayedStatus}</span><span className="workspace-badge">{definition.output_contract}</span></div></div><div className="prompt-editor-body"><dl className="prompt-metadata"><div><dt>Prompt Key</dt><dd>{definition.prompt_key}</dd></div><div><dt>Active Source</dt><dd>{definition.active.source === "CODE_FALLBACK" ? "Code Default" : "Database"}</dd></div><div><dt>Active Version</dt><dd>{definition.active.resolved_version}</dd></div></dl><textarea aria-label="System prompt" rows={20} readOnly={selected?.status !== "DRAFT"} value={displayedText} onChange={(event) => setDraftText(event.target.value)} />{message && <p className="repository-status"><CheckCircle2 size={15} />{message}</p>}{selected?.status === "DRAFT" && <div className="repository-actions"><button className="workspace-button" disabled={busy} onClick={saveDraft}><Save size={15} />Save Draft</button><button className="workspace-button workspace-primary" disabled={busy} onClick={() => activate(selected.version)}>Activate</button></div>}{selected?.status === "INACTIVE" && <div className="repository-actions"><button className="workspace-button" disabled={busy} onClick={() => activate(selected.version)}><RotateCcw size={15} />Activate Version</button></div>}</div></section>
      <aside className="workspace-panel prompt-history"><div className="workspace-panel-header"><h2>Version History</h2></div><div className="workspace-panel-body"><button className="workspace-row" onClick={() => chooseVersion(null)}><div><p className="workspace-row-title">Current resolution</p><p className="workspace-row-subtitle">{definition.active.resolved_version}</p></div><span className="workspace-badge">{definition.active.source === "CODE_FALLBACK" ? "Code Default" : "Active"}</span></button>{versions.map((version) => <button className="workspace-row" key={version.version} onClick={() => chooseVersion(version)}><div><p className="workspace-row-title">Version {version.version}</p><p className="workspace-row-subtitle">{version.created_by} · {new Date(version.created_at).toLocaleString()}</p></div><span className="workspace-badge">{version.status}</span></button>)}</div></aside></div>
  </div>;
}
