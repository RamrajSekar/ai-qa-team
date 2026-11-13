"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "@/utils/api";
import type { CatalogCase } from "./ProjectTestCatalog";

interface Design {
  title: string; purpose: string; role: string | null; preconditions: string[];
  public_data: Record<string, string>; procedure: { instruction: string; expected: string }[];
  assertions: string[]; cleanup: string[]; acceptance_criteria_refs: string[]; rule_references: string[];
}
interface Version { approved_by?: string; approved_by_display_name?: string; approved_by_project_role?: string | null; approved_at?: string; approval_policy?: string; version_id: string; status: string; stale: boolean; case: Design; content_digest: string }
interface ReviewState {
  approval_policy?: { admin_only: boolean; can_approve: boolean };
  active_version_id: string | null; review_required: boolean; context_ready: boolean; context_error: string | null;
  current_context: { story_snapshot: { acceptance_criteria: string }; knowledge_version_id: string | null; story_analysis_id: string | null; source_digest: string; source_context_changed: boolean } | null;
  approved_expected_rules: { claim_id: string; statement: string }[]; versions: Version[];
}
const clean = (values: string[]) => values.map(item => item.trim()).filter(Boolean);

export default function TestDesignReview({ testcase, projectId, canApprove }: { testcase: CatalogCase; projectId: string; canApprove: boolean }) {
  const [open, setOpen] = useState(false);
  return <details className="border rounded p-3" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary className="cursor-pointer font-medium">Review &amp; approve test case</summary>
    {open && <ReviewForm testcase={testcase} projectId={projectId} canApprove={canApprove} />}
  </details>;
}

function ReviewForm({ testcase, projectId, canApprove }: { testcase: CatalogCase; projectId: string; canApprove: boolean }) {
  const base = `/projects/${encodeURIComponent(projectId)}/test-design/cases/${encodeURIComponent(testcase.testcase_id)}`;
  const [state, setState] = useState<ReviewState | null>(null);
  const [design, setDesign] = useState<Design>({ title: testcase.title, purpose: testcase.purpose || testcase.description || testcase.title,
    role: testcase.role || null, preconditions: testcase.preconditions || [], public_data: testcase.public_data || {},
    procedure: testcase.steps.map(step => ({ instruction: step.description || step.action, expected: step.expected || "" })),
    assertions: testcase.assertions || [], cleanup: testcase.cleanup || [], acceptance_criteria_refs: testcase.acceptance_criteria_refs || [], rule_references: testcase.rule_references || [] });
  const [data, setData] = useState(JSON.stringify(testcase.public_data || {}, null, 2));
  const [parent, setParent] = useState<string | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [dirty, setDirty] = useState(true);
  const [approvalId, setApprovalId] = useState<string | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [message, setMessage] = useState("");
  const saveKey = useRef<{ fingerprint: string; key: string } | null>(null);
  const approvalSection = useRef<HTMLDivElement>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    const response = await apiFetch(base, { signal });
    if (!response.ok) throw new Error(typeof response.data?.detail === "string" ? response.data.detail : "Could not load test design review.");
    if (!signal?.aborted) { setState(response.data); setParent(response.data.active_version_id); }
  }, [base]);
  useEffect(() => { const controller = new AbortController(); void load(controller.signal).catch(failure => {
    if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Could not load test design review.");
  }); return () => controller.abort(); }, [load]);

  useEffect(() => {
    if (approvalId && !dirty) approvalSection.current?.scrollIntoView({ block: "end" });
  }, [approvalId, dirty]);

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
  function update(fields: Partial<Design>) { setDesign(current => ({ ...current, ...fields })); setDirty(true); setReviewed(false); }
  const assertions = clean(design.assertions);
  const criteria = state?.current_context?.story_snapshot.acceptance_criteria || "";
  const criterionOptions = Array.from(new Set([...criteria.split(/\r?\n/).map(item => item.trim()).filter(Boolean), ...design.acceptance_criteria_refs]));
  const rules = state?.approved_expected_rules || [];
  const unavailableRules = design.rule_references.filter(id => !rules.some(rule => rule.claim_id === id));
  const blockers: string[] = [];
  if (!state) blockers.push("Wait for test design review to load.");
  else if (!state.context_ready) blockers.push(state.context_error || "Review the source story and scenario first.");
  if (!design.title.trim()) blockers.push("Enter a test case title.");
  if (!design.purpose.trim()) blockers.push("Enter a purpose.");
  if (!design.procedure.length || design.procedure.some(step => !step.instruction.trim() || !step.expected.trim())) blockers.push("Each test step needs an action and an expected result.");
  if (design.acceptance_criteria_refs.some(quote => !criteria.includes(quote))) blockers.push("Replace acceptance-criteria links that are no longer in the story.");
  if (unavailableRules.length) blockers.push("Remove unavailable knowledge-rule links before saving.");
  if (state?.current_context?.source_context_changed && !acknowledged) blockers.push("Confirm that you reviewed the changed source context.");
  if (assertions.length > 20) blockers.push("Keep additional expected outcomes to 20 lines or fewer.");
  if (clean(design.cleanup).length > 15 || clean(design.preconditions).length > 15) blockers.push("Keep cleanup and preconditions to 15 lines each or fewer.");
  let publicData: Record<string, string> | null = null;
  try {
    const parsed: unknown = JSON.parse(data);
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object" || !Object.values(parsed).every(value => typeof value === "string")) throw new Error();
    publicData = parsed as Record<string, string>;
  } catch { blockers.push("Test data must be a JSON object containing text values."); }
  const activeVersion = state?.versions.find(version => version.version_id === state.active_version_id);
  const mayApprove = state?.approval_policy?.can_approve ?? canApprove;
  const adminOnly = state?.approval_policy?.admin_only ?? true;
  const candidate = state?.versions.find(version => version.version_id === approvalId && version.status === "draft") || state?.versions.find(version => version.status === "draft");

  async function save() {
    if (blockers.length || !publicData) throw new Error("Resolve the listed items before saving.");
    const content = { ...design, preconditions: clean(design.preconditions), assertions,
      cleanup: clean(design.cleanup), acceptance_criteria_refs: clean(design.acceptance_criteria_refs), rule_references: clean(design.rule_references),
      public_data: Object.entries(publicData).map(([name, value]) => ({ name, value })) };
    const fingerprint = JSON.stringify([content, parent, acknowledged, state?.current_context]);
    if (saveKey.current?.fingerprint !== fingerprint) saveKey.current = { fingerprint, key: crypto.randomUUID().replaceAll("-", "") };
    const version: Version = await post(base, { case: content, parent_version_id: parent, acknowledge_source_changes: acknowledged, idempotency_key: saveKey.current.key });
    await load(); setApprovalId(version.version_id); setDirty(false); setReviewed(false);
    setMessage("Draft saved. Review the saved steps and expected results below, then approve the test case.");
  }
  function copy(version: Version, forApproval = false) {
    setDesign(version.case); setData(JSON.stringify(version.case.public_data, null, 2)); setParent(state?.active_version_id || null);
    setAcknowledged(false); setReviewed(false); setDirty(!forApproval); setApprovalId(version.version_id); saveKey.current = null;
  }
  async function download(version: Version, format: "json" | "text") {
    const response = await apiFetch(`${base}/${version.version_id}/export?format=${format}`);
    if (!response.ok) throw new Error("Could not export this approved version.");
    const artifact = response.data;
    const url = URL.createObjectURL(new Blob([artifact.content], { type: artifact.media_type }));
    const link = document.createElement("a"); link.href = url; link.download = artifact.filename;
    document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 0);
    setMessage(version.stale ? "Historical approved version exported; its source context requires review." : "Approved test case exported for manual use.");
  }

  return <div className="space-y-4 mt-3 test-design-review">
    <div className="design-guide"><strong>1. Edit test steps → 2. Save draft → 3. Review &amp; approve</strong><p>Approval applies to an exact saved version. It does not start a test execution.</p></div>
    {state && <p role="status">{state.review_required ? "Test case needs review" : "An approved version is available"}</p>}
    {activeVersion?.approved_by && <p className="workspace-metadata">Approved by {activeVersion.approved_by_display_name || activeVersion.approved_by}{activeVersion.approved_by_project_role ? ` (${activeVersion.approved_by_project_role})` : ""}{activeVersion.approved_at ? ` · ${new Date(activeVersion.approved_at).toLocaleString()}` : ""}</p>}
    {!mayApprove && adminOnly && <p>A project administrator must approve the saved draft. You can prepare it for review.</p>}
    {error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    {!adminOnly && <p>Project-admin sign-off is not required. Any authorized project member can review and approve the saved version.</p>}
    <fieldset disabled={busy} className="space-y-3"><legend className="font-semibold">Test case draft</legend>
      <label className="block">Test case title<input className="border rounded w-full p-2" value={design.title} maxLength={240} onChange={event => update({ title: event.target.value })} /></label>
      <label className="block">Purpose<textarea className="border rounded w-full p-2" value={design.purpose} maxLength={1500} onChange={event => update({ purpose: event.target.value })} /></label>
      <label className="block">Application role (optional)<input className="border rounded w-full p-2" value={design.role || ""} maxLength={100} onChange={event => update({ role: event.target.value || null })} /></label>
      <label className="block">Preconditions (optional, one per line)<textarea className="border rounded w-full p-2" value={design.preconditions.join("\n")} onChange={event => update({ preconditions: event.target.value.split("\n") })} /></label>
      {design.procedure.map((step, index) => <div className="border rounded p-2 space-y-2" key={index}>
        <label className="block">Test step {index+1}<textarea aria-label={`Test step ${index+1}`} className="border rounded w-full p-2" value={step.instruction} maxLength={2000} onChange={event => update({ procedure: design.procedure.map((item, i) => i === index ? { ...item, instruction: event.target.value } : item) })} /></label>
        <label className="block">Expected result {index+1}<textarea aria-label={`Expected result ${index+1}`} className="border rounded w-full p-2" value={step.expected} maxLength={2000} onChange={event => update({ procedure: design.procedure.map((item, i) => i === index ? { ...item, expected: event.target.value } : item) })} /></label>
        <button className="workspace-button" onClick={() => update({ procedure: design.procedure.filter((_, i) => i !== index) })}>Remove Test Step {index+1}</button>
      </div>)}
      <button className="workspace-button" disabled={design.procedure.length >= 40} onClick={() => update({ procedure: [...design.procedure, { instruction: "", expected: "" }] })}>Add Test Step</button>
      <fieldset className="space-y-2"><legend className="font-semibold">Acceptance criteria covered (optional)</legend><p>Select relevant criteria when useful. These options come from the source story; you do not need to type reference IDs.</p>
        {!criterionOptions.length && <p>No criteria available to link.</p>}
        {criterionOptions.map((quote, index) => <label className="review-choice" key={quote}><input type="checkbox" checked={design.acceptance_criteria_refs.includes(quote)} disabled={!design.acceptance_criteria_refs.includes(quote) && design.acceptance_criteria_refs.length >= 15} onChange={event => update({ acceptance_criteria_refs: event.target.checked ? [...design.acceptance_criteria_refs, quote] : design.acceptance_criteria_refs.filter(value => value !== quote) })} /><span>Criterion {index+1}: {quote}{!criteria.includes(quote) && " (no longer in source story)"}</span></label>)}
      </fieldset>
      {(rules.length > 0 || unavailableRules.length > 0) && <fieldset className="space-y-2"><legend className="font-semibold">Related approved product rules (optional)</legend><p>Link only rules that define this case’s expected behavior. This is separate from approving the test case.</p>
        {rules.map(rule => <label className="review-choice" key={rule.claim_id}><input type="checkbox" checked={design.rule_references.includes(rule.claim_id)} disabled={!design.rule_references.includes(rule.claim_id) && design.rule_references.length >= 30} onChange={event => update({ rule_references: event.target.checked ? [...design.rule_references, rule.claim_id] : design.rule_references.filter(id => id !== rule.claim_id) })} /><span>{rule.statement}</span></label>)}
        {unavailableRules.length > 0 && <div><p>Some existing rule links are unavailable in the approved knowledge version.</p><button className="workspace-button" onClick={() => update({ rule_references: design.rule_references.filter(id => !unavailableRules.includes(id)) })}>Remove unavailable rule links</button></div>}
      </fieldset>}
      <details><summary>Additional outcomes, cleanup and test data (optional)</summary><div className="space-y-3 mt-3">
        <p>These fields are optional for approval. Every test step’s expected result remains a required check, even when no additional outcomes are entered.</p>
        <label className="block">Additional expected outcomes (one per line)<textarea className="border rounded w-full p-2" value={design.assertions.join("\n")} onChange={event => update({ assertions: event.target.value.split("\n") })} /></label>
        <label className="block">Cleanup / restore state (one per line)<textarea className="border rounded w-full p-2" value={design.cleanup.join("\n")} onChange={event => update({ cleanup: event.target.value.split("\n") })} /></label>
        <p>Cleanup describes how to restore data changed by this case. Leave it blank when nothing needs restoring.</p>
        <label className="block">Test data (JSON text values; no secrets)<textarea className="border rounded w-full p-2" rows={3} value={data} maxLength={10000} onChange={event => { setData(event.target.value); setDirty(true); setReviewed(false); }} /></label>
      </div></details>
      {state?.current_context?.source_context_changed && <label className="review-choice"><input type="checkbox" checked={acknowledged} onChange={event => { setAcknowledged(event.target.checked); setDirty(true); setReviewed(false); }} />I reviewed copied content against changed approved knowledge and story analysis.</label>}
      {blockers.length > 0 && <div className="design-guide" role="status"><strong>Before saving</strong><ul>{blockers.map(item => <li key={item}>{item}</li>)}</ul></div>}
      <button className="workspace-button workspace-primary" disabled={busy || blockers.length > 0} onClick={() => void action(save)}>Save test case draft</button>
    </fieldset>
    <div ref={approvalSection} className="design-guide space-y-3" role="region" aria-label="Test case approval">
      <h3 className="font-semibold">Review &amp; approve saved draft</h3>
      {!candidate ? <p>{state?.active_version_id ? "This test case already has an approved version. Save a successor draft only when changes are needed." : "Save a draft first. The approval action becomes available after an authorized reviewer reviews its saved content."}</p> : <>
        <p>{candidate.case.title}{candidate.stale ? " · source changed; save a reviewed successor draft" : " · saved draft"}</p>
        {dirty ? <button className="workspace-button" disabled={busy} onClick={() => copy(candidate, true)}>Review saved draft</button> : <>
          <ol className="list-decimal pl-6">{candidate.case.procedure.map((step, index) => <li key={index}><p>{step.instruction}</p><p>Expected: {step.expected}</p></li>)}</ol>
          <p>Additional outcomes: {candidate.case.assertions.join("; ") || "None"}</p><p>Acceptance-criteria links: {candidate.case.acceptance_criteria_refs.join("; ") || "None selected"}</p>
          <details><summary>All saved fields</summary><pre className="whitespace-pre-wrap text-sm">{JSON.stringify(candidate.case, null, 2)}</pre></details>
          {mayApprove && <label className="review-choice"><input type="checkbox" disabled={busy || candidate.stale} checked={reviewed} onChange={event => setReviewed(event.target.checked)} />I reviewed the saved test steps, expected results and source links.</label>}
        </>}
      </>}
      {mayApprove && <button className="workspace-button workspace-primary" disabled={busy || !candidate || candidate.stale || dirty || !reviewed} onClick={() => candidate && void action(async () => { await post(`${base}/${candidate.version_id}/approve`, {}); await load(); setReviewed(false); setMessage("Test case approved. No execution was started."); })}>Approve Test Case</button>}
      {candidate && dirty && <p>Editor changes are not included in the saved draft. Save your changes, or choose Review saved draft to load that exact version.</p>}
    </div>
    <button className="workspace-button" disabled={busy} onClick={() => void action(load)}>Refresh design review</button>
    {!!state?.versions.length && <details><summary>Saved version history and exports</summary>{state.versions.map(version => <details key={version.version_id} className="border rounded p-3"><summary>{version.case.title} · {version.status}{version.stale ? " · source review required" : ""}</summary>
      <pre className="whitespace-pre-wrap text-sm">{JSON.stringify(version.case, null, 2)}</pre><p className="workspace-metadata">Version {version.version_id} · Digest {version.content_digest}</p>
      {version.approved_by && <p>Approved by {version.approved_by_display_name || version.approved_by} · User {version.approved_by}{version.approved_by_project_role ? ` · Project role ${version.approved_by_project_role}` : ""}{version.approved_at ? ` · ${new Date(version.approved_at).toLocaleString()}` : ""}{version.approval_policy ? ` · Policy: ${version.approval_policy.replaceAll("_", " ")}` : ""}</p>}
      <button className="workspace-button" disabled={busy} onClick={() => copy(version)}>Copy into successor editor</button>
      {version.status === "draft" && <button className="workspace-button" disabled={busy} onClick={() => copy(version, true)}>Review this saved draft</button>}
      {version.status === "approved" && <><button className="workspace-button" disabled={busy} onClick={() => void action(() => download(version, "text"))}>Export approved text</button><button className="workspace-button" disabled={busy} onClick={() => void action(() => download(version, "json"))}>Export approved JSON</button></>}
    </details>)}</details>}
  </div>;
}
