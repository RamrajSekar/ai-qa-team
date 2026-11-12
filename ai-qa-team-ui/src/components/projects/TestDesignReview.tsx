"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "@/utils/api";
import type { CatalogCase } from "./ProjectTestCatalog";

interface Design {
  title: string; purpose: string; role: string | null; preconditions: string[];
  public_data: Record<string, string>; procedure: { instruction: string; expected: string }[];
  assertions: string[]; cleanup: string[]; acceptance_criteria_refs: string[]; rule_references: string[];
}
interface Version { version_id: string; status: string; stale: boolean; case: Design; content_digest: string }
interface ReviewState {
  active_version_id: string | null; review_required: boolean; context_ready: boolean; context_error: string | null;
  current_context: { story_snapshot: { acceptance_criteria: string }; knowledge_version_id: string; story_analysis_id: string; source_digest: string; source_context_changed: boolean } | null;
  approved_expected_rules: { claim_id: string; statement: string }[]; versions: Version[];
}
const clean = (values: string[]) => values.map(item => item.trim()).filter(Boolean);

export default function TestDesignReview({ testcase, projectId, canApprove }: { testcase: CatalogCase; projectId: string; canApprove: boolean }) {
  const [open, setOpen] = useState(false);
  return <details className="border rounded p-3" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary className="cursor-pointer font-medium">Review &amp; approve natural-language test design</summary>
    {open && <ReviewForm testcase={testcase} projectId={projectId} canApprove={canApprove} />}
  </details>;
}

function ReviewForm({ testcase, projectId, canApprove }: { testcase: CatalogCase; projectId: string; canApprove: boolean }) {
  const base = `/projects/${encodeURIComponent(projectId)}/test-design/cases/${encodeURIComponent(testcase.testcase_id)}`;
  const [state, setState] = useState<ReviewState | null>(null);
  const [design, setDesign] = useState<Design>({ title: testcase.title, purpose: testcase.purpose || testcase.description || "",
    role: testcase.role || null, preconditions: testcase.preconditions || [], public_data: testcase.public_data || {},
    procedure: testcase.steps.map(step => ({ instruction: step.description || step.action, expected: step.expected || "" })),
    assertions: testcase.assertions || [], cleanup: testcase.cleanup || [], acceptance_criteria_refs: testcase.acceptance_criteria_refs || [], rule_references: testcase.rule_references || [] });
  const [data, setData] = useState(JSON.stringify(testcase.public_data || {}, null, 2));
  const [parent, setParent] = useState<string | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [message, setMessage] = useState("");
  const saveKey = useRef<{ fingerprint: string; key: string } | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    const response = await apiFetch(base, { signal });
    if (!response.ok) throw new Error(typeof response.data?.detail === "string" ? response.data.detail : "Could not load test design review.");
    if (!signal?.aborted) { setState(response.data); setParent(response.data.active_version_id); }
  }, [base]);
  useEffect(() => { const controller = new AbortController(); void load(controller.signal).catch(failure => {
    if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Could not load test design review.");
  }); return () => controller.abort(); }, [load]);

  async function action(work: () => Promise<void>) {
    setBusy(true); setError(""); setMessage("");
    try { await work(); } catch (failure) { setError(failure instanceof Error ? failure.message : "Request failed."); }
    finally { setBusy(false); }
  }
  async function post(path: string, body: object) {
    const response = await apiFetch(path, { method: "POST", body: JSON.stringify(body) });
    if (!response.ok) throw new Error(typeof response.data?.detail === "string" ? response.data.detail : "Check all required fields and source references.");
    return response.data;
  }
  function update(fields: Partial<Design>) { setDesign(current => ({ ...current, ...fields })); }
  async function save() {
    const publicData: unknown = JSON.parse(data);
    if (!publicData || Array.isArray(publicData) || typeof publicData !== "object" || !Object.values(publicData).every(value => typeof value === "string")) {
      throw new Error("Public data must be a JSON object with text values. Do not include credentials or personal data.");
    }
    const content = { ...design, preconditions: clean(design.preconditions), assertions: clean(design.assertions),
      cleanup: clean(design.cleanup), acceptance_criteria_refs: clean(design.acceptance_criteria_refs), rule_references: clean(design.rule_references),
      public_data: Object.entries(publicData).map(([name, value]) => ({ name, value })) };
    const fingerprint = JSON.stringify([content, parent, acknowledged, state?.current_context]);
    if (saveKey.current?.fingerprint !== fingerprint) saveKey.current = { fingerprint, key: crypto.randomUUID().replaceAll("-", "") };
    await post(base, { case: content, parent_version_id: parent, acknowledge_source_changes: acknowledged, idempotency_key: saveKey.current.key });
    await load(); setMessage("Immutable design draft saved. Review its saved content before approval.");
  }
  async function download(version: Version, format: "json" | "text") {
    const response = await apiFetch(`${base}/${version.version_id}/export?format=${format}`);
    if (!response.ok) throw new Error("Could not export this approved version.");
    const artifact = response.data;
    const url = URL.createObjectURL(new Blob([artifact.content], { type: artifact.media_type }));
    const link = document.createElement("a"); link.href = url; link.download = artifact.filename;
    document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 0);
    setMessage(version.stale ? "Historical approved version exported; its source context requires review." : "Approved natural-language design exported for manual use.");
  }
  const valid = design.title.trim() && design.purpose.trim() && design.procedure.length && design.procedure.every(step => step.instruction.trim() && step.expected.trim())
    && clean(design.assertions).length && clean(design.acceptance_criteria_refs).length;

  return <div className="space-y-4 mt-3">
    <p>Review purpose, data, detailed steps and explicit expectations. Approval creates a Test Design version for manual use; it does not start automation.</p>
    {state && <p role="status">{state.review_required ? "Design review required" : "Current approved design"}{state.active_version_id ? ` · ${state.active_version_id}` : ""}</p>}
    {state?.context_error && <p role="alert">{state.context_error}</p>}
    {state?.current_context && <details><summary>Review current source context</summary>
      <p className="whitespace-pre-wrap">Acceptance criteria: {state.current_context.story_snapshot.acceptance_criteria}</p>
      <p>Knowledge version: {state.current_context.knowledge_version_id}</p><p>Story analysis: {state.current_context.story_analysis_id}</p>
      {state.approved_expected_rules.map(rule => <p key={rule.claim_id}>{rule.claim_id}: {rule.statement}</p>)}
    </details>}
    <fieldset disabled={busy} className="space-y-3"><legend className="font-semibold">Successor draft editor</legend>
      <label className="block">Design title<input className="border rounded w-full p-2" value={design.title} maxLength={240} onChange={event => update({ title: event.target.value })} /></label>
      <label className="block">Design purpose<textarea className="border rounded w-full p-2" value={design.purpose} maxLength={1500} onChange={event => update({ purpose: event.target.value })} /></label>
      <label className="block">Application role<input className="border rounded w-full p-2" value={design.role || ""} maxLength={100} onChange={event => update({ role: event.target.value || null })} /></label>
      <label className="block">Preconditions (one per line)<textarea className="border rounded w-full p-2" value={design.preconditions.join("\n")} onChange={event => update({ preconditions: event.target.value.split("\n") })} /></label>
      <label className="block">Public data (JSON text values; no secrets)<textarea className="border rounded w-full p-2" rows={3} value={data} maxLength={10000} onChange={event => setData(event.target.value)} /></label>
      {design.procedure.map((step, index) => <div className="border rounded p-2 space-y-2" key={index}>
        <label className="block">Instruction {index+1}<textarea className="border rounded w-full p-2" value={step.instruction} maxLength={2000} onChange={event => update({ procedure: design.procedure.map((item, i) => i === index ? { ...item, instruction: event.target.value } : item) })} /></label>
        <label className="block">Expected result {index+1}<textarea className="border rounded w-full p-2" value={step.expected} maxLength={2000} onChange={event => update({ procedure: design.procedure.map((item, i) => i === index ? { ...item, expected: event.target.value } : item) })} /></label>
        <button className="workspace-button" onClick={() => update({ procedure: design.procedure.filter((_, i) => i !== index) })}>Remove instruction {index+1}</button>
      </div>)}
      <button className="workspace-button" disabled={design.procedure.length >= 40} onClick={() => update({ procedure: [...design.procedure, { instruction: "", expected: "" }] })}>Add design instruction</button>
      <label className="block">Required assertions (one per line)<textarea className="border rounded w-full p-2" value={design.assertions.join("\n")} onChange={event => update({ assertions: event.target.value.split("\n") })} /></label>
      <label className="block">Cleanup (one per line)<textarea className="border rounded w-full p-2" value={design.cleanup.join("\n")} onChange={event => update({ cleanup: event.target.value.split("\n") })} /></label>
      <label className="block">Exact acceptance criteria excerpts (one per line)<textarea className="border rounded w-full p-2" value={design.acceptance_criteria_refs.join("\n")} onChange={event => update({ acceptance_criteria_refs: event.target.value.split("\n") })} /></label>
      <label className="block">Approved rule IDs (one per line)<textarea className="border rounded w-full p-2" value={design.rule_references.join("\n")} onChange={event => update({ rule_references: event.target.value.split("\n") })} /></label>
      {state?.current_context?.source_context_changed && <label className="block"><input type="checkbox" checked={acknowledged} onChange={event => setAcknowledged(event.target.checked)} /> I reviewed copied content against the changed approved knowledge and story analysis.</label>}
      <button className="workspace-button" disabled={!valid || !state?.context_ready || (state.current_context?.source_context_changed && !acknowledged)} onClick={() => void action(save)}>Save test design draft</button>
    </fieldset>
    <button className="workspace-button" disabled={busy} onClick={() => void action(load)}>Refresh design review</button>
    {state?.versions.map(version => <details key={version.version_id} className="border rounded p-3"><summary>{version.case.title} · {version.status}{version.stale ? " · source review required" : ""} · {version.version_id}</summary>
      <pre className="whitespace-pre-wrap text-sm">{JSON.stringify(version.case, null, 2)}</pre><p>Content digest: {version.content_digest}</p>
      <button className="workspace-button" disabled={busy} onClick={() => { setDesign(version.case); setData(JSON.stringify(version.case.public_data, null, 2)); setParent(state.active_version_id); setAcknowledged(false); saveKey.current = null; }}>Copy into successor editor</button>
      {canApprove && version.status === "draft" && <button className="workspace-button" disabled={busy || version.stale} onClick={() => void action(async () => { await post(`${base}/${version.version_id}/approve`, {}); await load(); setMessage("Test design approved. No browser execution was started."); })}>Approve test design version</button>}
      {version.status === "approved" && <><button className="workspace-button" disabled={busy} onClick={() => void action(() => download(version, "text"))}>Export approved text</button><button className="workspace-button" disabled={busy} onClick={() => void action(() => download(version, "json"))}>Export approved JSON</button></>}
    </details>)}
    {error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}
  </div>;
}
