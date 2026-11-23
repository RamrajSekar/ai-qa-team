"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { IconAction } from "@/components/ui/icon-action";
import { WorkspaceDialog } from "@/components/ui/workspace-dialog";
import { apiFetch } from "@/utils/api";

type Draft = { title: string; summary: string; steps: string[]; expected_result: string; actual_result: string; environment?: string; context: string; missing_information: string[] };
type Bug = { bug_id: string; kind: string; url: string | null; draft: Draft | null };
export default function AttemptBugPanel({ projectId, runId, compact = false }: { projectId: string; runId: string; compact?: boolean }) {
  const base = `/projects/${encodeURIComponent(projectId)}/test-results/attempts/${encodeURIComponent(runId)}`;
  const [mode, setMode] = useState<"draft" | "external" | "links" | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [links, setLinks] = useState<Bug[]>([]);
  const [copyNotice, setCopyNotice] = useState("");
  const [proposal, setProposal] = useState<string | null>(null);
  const [url, setUrl] = useState(""); const [reviewed, setReviewed] = useState(false);
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [message, setMessage] = useState("");
  const requestKey = useRef<{content: string; key: string} | null>(null);
  const load = useCallback(async () => {
    const response = await apiFetch(`${base}/bugs`, { cache: "no-store" });
    if (!response.ok) throw new Error("Could not load bugs for this attempt.");
    setDraft(current => current || response.data.draft); setLinks(response.data.links);
  }, [base]);
  useEffect(() => { if (mode && !draft) void load().catch(() => setError("Could not load bug details. Close and reopen to try again.")); }, [mode, draft, load]);
  function edit(key: keyof Draft, value: string) {
    setCopyNotice(""); setReviewed(false); setDraft(current => current && { ...current, [key]: ["steps", "missing_information"].includes(key) ? value.split("\n") : value });
  }
  async function save() {
    if (!reviewed || !draft || mode === "links" || !mode || (mode === "draft" && !draft.environment?.trim())) return;
    const payload = { kind: mode, reviewed: true, draft: mode === "draft" ? draft : null, url: mode === "external" ? url : null, proposal_id: mode === "draft" ? proposal : null };
    const content = JSON.stringify(payload);
    if (requestKey.current?.content !== content) requestKey.current = { content, key: crypto.randomUUID().replaceAll("-", "") };
    setBusy(true); setError(""); setMessage("");
    try {
      const response = await apiFetch(`${base}/bugs`, { method: "POST", body: JSON.stringify({ ...payload, idempotency_key: requestKey.current.key }) });
      if (!response.ok) throw new Error(typeof response.data?.detail === "string" ? response.data.detail : "Could not save this bug. Check the fields and HTTPS URL.");
      requestKey.current = null; await load(); setMode("links"); setReviewed(false);
      setMessage(mode === "draft" ? "Bug draft saved locally. Nothing was published externally." : "Bug linked. The URL was not fetched.");
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Save was not confirmed. Retry unchanged content to recover the same link."); }
    finally { setBusy(false); }
  }
  async function draftAI() {
    setBusy(true); setError(""); setMessage(""); setCopyNotice(""); setReviewed(false);
    try {
      const response = await apiFetch(`${base}/bug-draft-ai`, { method: "POST" });
      if (!response.ok) throw new Error(typeof response.data?.detail === "string" ? response.data.detail : response.data?.detail?.message || "AI drafting was not confirmed. Use manual drafting; do not automatically retry.");
      setDraft(current => ({ ...response.data.draft, environment: current?.environment || response.data.draft.environment || "" })); setProposal(response.data.proposal_id);
    } catch (failure) { setError(failure instanceof Error ? failure.message : "AI drafting unavailable. Manual drafting remains available."); }
    finally { setBusy(false); }
  }
  const panelTitle = mode === "draft" ? "Draft Bug" : mode === "external" ? "Link Bug" : "Bugs";
  const report = draft ? [
    `Title: ${draft.title}`, `Summary:
${draft.summary}`,
    `Steps to reproduce:
${draft.steps.map((step, index) => `${index + 1}. ${step}`).join("\n")}`,
    `Environment:
${draft.environment || ""}`, `Expected result:
${draft.expected_result}`,
    `Actual result:
${draft.actual_result}`,
  ].join("\n\n") : "";
  async function copyReport() {
    if (!draft || busy) return;
    try { await navigator.clipboard.writeText(report); setCopyNotice("Report copied."); }
    catch { setCopyNotice("Select the report and copy it manually."); }
  }
  const actions = <div className="workspace-actions">
    {compact ? <><IconAction action="bug" label="Create bug" disabled={busy} onClick={() => { setMode("draft"); setReviewed(false); }} /><IconAction action="link" label="Link existing bug" disabled={busy} onClick={() => { setMode("external"); setReviewed(false); }} /><IconAction action="bugs" label="View linked bugs" disabled={busy} onClick={() => setMode("links")} /></> : <><button type="button" className="workspace-button" disabled={busy} onClick={() => { setMode("draft"); setReviewed(false); }}>Create bug</button><button type="button" className="workspace-button" disabled={busy} onClick={() => { setMode("external"); setReviewed(false); }}>Link existing bug</button><button type="button" className="workspace-button" disabled={busy} onClick={() => setMode("links")}>View linked bugs</button></>}
  </div>;
  const content = <>{actions}
    {error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    {mode && !draft && !error && <p role="status">Loading bug details…</p>}
    {mode && draft && <>
      {mode === "draft" && <fieldset disabled={busy} className="space-y-3"><legend>Bug report</legend>
        <label className="block">Bug title<input aria-label="Bug title" className="block w-full border rounded p-2" maxLength={240} value={draft.title} onChange={event => edit("title", event.target.value)} /></label>
        <label className="block">Environment<input aria-label="Environment" type="text" required maxLength={240} value={draft.environment || ""} onChange={event => edit("environment", event.target.value)} className="block w-full border rounded p-2" /></label>
        <label className="block">Bug summary<textarea aria-label="Bug summary" className="block w-full border rounded p-2" rows={3} value={draft.summary} onChange={event => edit("summary", event.target.value)} /></label>
        <div className="workspace-actions"><button type="button" className="workspace-button" onClick={() => void draftAI()}>Draft with AI</button><span className="workspace-metadata">Uses your AI allowance.</span></div>
        <details><summary>Edit steps and results</summary><div className="space-y-3 mt-3">
          {([['steps','Reproduction steps (one per line)'],['expected_result','Expected result'],['actual_result','Actual result'],['missing_information','Missing information (one per line)']] as const).map(([key,label]) => <label className="block" key={key}>{label}<textarea aria-label={label} className="block w-full border rounded p-2" value={Array.isArray(draft[key]) ? draft[key].join("\n") : draft[key]} onChange={event => edit(key,event.target.value)} /></label>)}
        </div></details>
        <label className="block">Report to copy<textarea aria-label="Report to copy" readOnly rows={16} className="block w-full border rounded p-2" value={report} /></label>
        <button type="button" className="workspace-button" disabled={busy} onClick={() => void copyReport()}>Copy report</button>
        {copyNotice && <p role="status">{copyNotice}</p>}
      </fieldset>}
      {mode === "external" && <label>Existing bug HTTPS URL<input aria-label="Existing bug HTTPS URL" type="url" maxLength={2000} disabled={busy} value={url} onChange={event => {setUrl(event.target.value);setReviewed(false);}} /></label>}
      {mode !== "links" && <><label className="manual-expectation"><input type="checkbox" disabled={busy} checked={reviewed} onChange={event => setReviewed(event.target.checked)} />I reviewed this bug information and its link to this attempt.</label>{mode === "draft" && !draft.environment?.trim() && <p className="workspace-metadata">Enter an environment before saving.</p>}<button type="button" className="workspace-button workspace-primary" disabled={busy || !reviewed || (mode === "draft" && !draft.environment?.trim()) || (mode === "external" && !url.startsWith("https://"))} onClick={() => void save()}>{mode === "draft" ? "Save bug draft" : "Save bug link"}</button></>}
      <h4>Linked bugs</h4>{!links.length && <p>No bugs linked yet.</p>}{links.map(bug => <div key={bug.bug_id}>{bug.url ? <a className="design-back-link" href={bug.url} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">Open linked bug</a> : <details><summary>{bug.draft?.title} · Local draft</summary><pre className="whitespace-pre-wrap">{JSON.stringify(Object.fromEntries(Object.entries(bug.draft || {}).filter(([key]) => key !== "context")),null,2)}</pre></details>}</div>)}
    </>}
  </>;
  return compact ? <section aria-label="Bugs for attempt">{actions}<WorkspaceDialog open={!!mode} title={panelTitle} onClose={() => setMode(null)} busy={busy} className="workspace-dialog-wide"><div className="design-page"><h2>{panelTitle}</h2>{content}</div></WorkspaceDialog></section> : <section className="space-y-3 border rounded p-3" aria-label="Bugs for attempt">{content}</section>;
}
