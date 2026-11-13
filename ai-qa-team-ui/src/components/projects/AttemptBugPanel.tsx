"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "@/utils/api";

type Draft = { title: string; summary: string; steps: string[]; expected_result: string; actual_result: string; context: string; missing_information: string[] };
type Bug = { bug_id: string; kind: string; url: string | null; draft: Draft | null };
export default function AttemptBugPanel({ projectId, runId }: { projectId: string; runId: string }) {
  const base = `/projects/${encodeURIComponent(projectId)}/test-results/attempts/${encodeURIComponent(runId)}`;
  const [mode, setMode] = useState<"draft" | "external" | "links" | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [links, setLinks] = useState<Bug[]>([]);
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
    setReviewed(false); setDraft(current => current && { ...current, [key]: ["steps", "missing_information"].includes(key) ? value.split("\n") : value });
  }
  async function save() {
    if (!reviewed || !draft || mode === "links" || !mode) return;
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
    setBusy(true); setError(""); setMessage(""); setReviewed(false);
    try {
      const response = await apiFetch(`${base}/bug-draft-ai`, { method: "POST" });
      if (!response.ok) throw new Error(typeof response.data?.detail === "string" ? response.data.detail : response.data?.detail?.message || "AI drafting was not confirmed. Use manual drafting; do not automatically retry.");
      setDraft(response.data.draft); setProposal(response.data.proposal_id);
      setMessage("AI summary proposed from the saved attempt. Review all fields before saving; current unsaved edits were replaced.");
    } catch (failure) { setError(failure instanceof Error ? failure.message : "AI drafting unavailable. Manual drafting remains available."); }
    finally { setBusy(false); }
  }
  return <section className="space-y-3 border rounded p-3" aria-label="Bugs for failed attempt">
    <div className="workspace-actions"><button type="button" className="workspace-button" disabled={busy} onClick={() => { setMode("draft"); setReviewed(false); }}>Create bug</button><button type="button" className="workspace-button" disabled={busy} onClick={() => { setMode("external"); setReviewed(false); }}>Link existing bug</button><button type="button" className="workspace-button" disabled={busy} onClick={() => setMode("links")}>View linked bugs</button></div>
    {error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    {mode && !draft && !error && <p role="status">Loading bug details…</p>}
    {mode && draft && <>
      <p>Links belong to this failed attempt and exact approved test version. Use nonsensitive information only.</p>
      {mode === "draft" && <fieldset disabled={busy} className="space-y-3"><legend>Review bug draft</legend>
        {([['title','Bug title'],['summary','Bug summary'],['steps','Reproduction steps (one per line)'],['expected_result','Expected result'],['actual_result','Observed actual result'],['context','Bug context'],['missing_information','Missing information (one per line)']] as const).map(([key,label]) => <label className="block" key={key}>{label}<textarea aria-label={label} className="block w-full border rounded p-2" value={Array.isArray(draft[key]) ? draft[key].join("\n") : draft[key]} onChange={event => edit(key,event.target.value)} /></label>)}
        <p>Draft with AI uses your project’s configured mode and AI request allowance. It proposes a summary from saved facts and replaces unsaved draft edits.</p>
        <button type="button" className="workspace-button" onClick={() => void draftAI()}>Draft with AI</button>
      </fieldset>}
      {mode === "external" && <label>Existing bug HTTPS URL<input aria-label="Existing bug HTTPS URL" type="url" maxLength={2000} disabled={busy} value={url} onChange={event => {setUrl(event.target.value);setReviewed(false);}} /></label>}
      {mode !== "links" && <><label className="manual-expectation"><input type="checkbox" disabled={busy} checked={reviewed} onChange={event => setReviewed(event.target.checked)} />I reviewed this bug information and its link to the failed attempt.</label><button type="button" className="workspace-button workspace-primary" disabled={busy || !reviewed || (mode === "external" && !url.startsWith("https://"))} onClick={() => void save()}>{mode === "draft" ? "Save bug draft" : "Save bug link"}</button></>}
      <h4>Linked bugs</h4>{!links.length && <p>No bugs linked yet.</p>}{links.map(bug => <div key={bug.bug_id}>{bug.url ? <a className="design-back-link" href={bug.url} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">Open linked bug</a> : <details><summary>{bug.draft?.title} · Local draft</summary><pre className="whitespace-pre-wrap">{JSON.stringify(bug.draft,null,2)}</pre></details>}</div>)}
    </>}
  </section>;
}
