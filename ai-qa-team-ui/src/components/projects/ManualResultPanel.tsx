"use client";
import AttemptBugPanel from "./AttemptBugPanel";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "@/utils/api";
import { WorkspaceDialog } from "@/components/ui/workspace-dialog";
import { DesignBadge } from "./DesignWorkspace";

type Verdict = "passed" | "failed" | "blocked" | "needs_review" | "cancelled";
const labels: Record<Verdict, string> = { passed: "Passed", failed: "Failed", blocked: "Blocked", needs_review: "Needs review", cancelled: "Cancelled" };
interface Version { version_id: string; case: { title: string; purpose?: string; preconditions?: string[]; procedure: { instruction: string; expected: string }[] }; expectations: { id: string; text: string }[] }
interface Result { execution_id?: string | null; run_id: string; mode: string; lifecycle: string; verdict: Verdict; actual_result: string; executor_id: string; executor_display_name?: string | null; recorded_at: string; specification: { approved_by?: string; approved_by_display_name?: string; approved_at?: string; version_id: string; case: Version["case"] }; environment?: { name?: string; env_id: string } | null }
interface State { eligible_version: Version | null; reason: string | null; records: Result[]; has_more: boolean; environments: { env_id: string; name: string }[] }

export default function ManualResultPanel({ projectId, testcaseId, title, onClose, onSaved, executionId }: {
  projectId: string; testcaseId: string; title: string; onClose: () => void; onSaved: () => Promise<void>; executionId?: string;
}) {
  const base = `/projects/${encodeURIComponent(projectId)}/test-results/cases/${encodeURIComponent(testcaseId)}`;
  const [state, setState] = useState<State | null>(null);
  const [skip, setSkip] = useState(0);
  const [actual, setActual] = useState("");
  const [verdict, setVerdict] = useState<Verdict | "">("");
  const [environment, setEnvironment] = useState("");
  const [verified, setVerified] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const saveKey = useRef<{ fingerprint: string; key: string } | null>(null);
  const load = useCallback(async (signal?: AbortSignal) => {
    const response = await apiFetch(`${base}?skip=${skip}`, { signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(15000)]) : AbortSignal.timeout(15000), cache: "no-store" });
    if (!response.ok) throw new Error(typeof response.data?.detail === "string" ? response.data.detail : "Could not load manual results.");
    if (executionId) {
      const executionResponse = await apiFetch(`/projects/${encodeURIComponent(projectId)}/test-results/executions/${encodeURIComponent(executionId)}`, { signal, cache: "no-store" });
      if (!executionResponse.ok) throw new Error("Could not load the pinned execution.");
      const execution = executionResponse.data;
      const pinned = execution.manifest.cases.find((item: { testcase_id: string }) => item.testcase_id === testcaseId);
      if (!pinned) throw new Error("Case is not selected in this execution.");
      const records: Result[] = execution.results.filter((item: { testcase_id: string }) => item.testcase_id === testcaseId);
      if (!signal?.aborted) { setState({ ...response.data, eligible_version: records.length ? null : { version_id: pinned.specification.version_id, case: pinned.specification.case, expectations: execution.expectations[testcaseId] }, reason: records.length ? "Result already recorded. Create a new execution to test again; this attempt is immutable." : null, records, has_more: false }); setEnvironment(execution.manifest.environment?.env_id || ""); }
    } else if (!signal?.aborted) setState(response.data);
  }, [base, skip, executionId, projectId, testcaseId]);
  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal).catch(failure => { if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Could not load results."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [load]);
  const version = state?.eligible_version;
  const allVerified = !!version?.expectations.length && version.expectations.every(item => verified.includes(item.id));
  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!version || !verdict) return;
    setBusy(true); setError(""); setMessage("");
    const content = { execution_id: executionId || null, version_id: version.version_id, actual_result: actual.trim(), verdict, verified_expectation_ids: verified, environment_id: environment || null };
    const fingerprint = JSON.stringify(content);
    if (saveKey.current?.fingerprint !== fingerprint) saveKey.current = { fingerprint, key: crypto.randomUUID().replaceAll("-", "") };
    try {
      const response = await apiFetch(base, { method: "POST", body: JSON.stringify({ ...content, idempotency_key: saveKey.current.key }), signal: AbortSignal.timeout(15000) });
      if (!response.ok) throw new Error(typeof response.data?.detail === "string" ? response.data.detail : "Could not save the manual result.");
      setActual(""); setVerdict(""); setVerified([]); saveKey.current = null;
      setMessage("Manual result saved as a separate attempt. The test specification is unchanged.");
      if (skip) { setLoading(true); setSkip(0); } else await load();
      await onSaved();
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Save was not confirmed. Retry unchanged content to safely recover the same attempt."); }
    finally { setBusy(false); }
  }
  function historyPage(next: number) { setLoading(true); setError(""); setSkip(next); }
  return <WorkspaceDialog open title={`Manual results: ${title}`} onClose={onClose} busy={busy} className="workspace-dialog-wide">
    <div className="design-page manual-results"><header><p className="workspace-eyebrow">Manual testing</p><h2 className="text-xl font-semibold">{title}</h2><p>Each save creates an independent attempt against an exact approved design version. Use nonsensitive observations only; never enter credentials.</p></header>
      {error && <div role="alert"><p>{error}</p><button className="workspace-button" disabled={busy} onClick={() => { setError(""); setLoading(true); void load().catch(() => setError("Could not reload results.")).finally(() => setLoading(false)); }}>Refresh results</button></div>}
      {message && <p role="status">{message}</p>}
      {loading ? <p role="status">Loading manual results…</p> : state && <>
        {version ? <form onSubmit={event => void save(event)} className="space-y-4">
          <p className="workspace-metadata">Approved test specification · {executionId ? "pinned at execution creation" : "eligibility checked again when saving"}</p>
          <details><summary>Approved procedure and expected results</summary><p>{version.case.purpose}</p><p>{version.case.preconditions?.join("; ")}</p><ol className="list-decimal pl-6">{version.case.procedure.map((step, i) => <li key={i}><p>{step.instruction}</p><p>Expected: {step.expected}</p></li>)}</ol></details>
          <label>Environment (optional)<select aria-label="Environment (optional)" disabled={busy || !!executionId} value={environment} onChange={event => setEnvironment(event.target.value)}><option value="">Not specified</option>{state.environments.map(env => <option key={env.env_id} value={env.env_id}>{env.name}</option>)}</select></label>
          <label>Actual result<textarea rows={4} maxLength={5000} required disabled={busy} value={actual} onChange={event => setActual(event.target.value)} /></label>
          <label>Result<select aria-label="Result" required disabled={busy} value={verdict} onChange={event => setVerdict(event.target.value as Verdict | "")}><option value="">Select a result</option>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          {verdict === "passed" && <fieldset disabled={busy} className="space-y-2"><legend>Confirm every approved expectation was checked and satisfied</legend>{version.expectations.map(item => <label className="manual-expectation" key={item.id}><input type="checkbox" checked={verified.includes(item.id)} onChange={event => setVerified(ids => event.target.checked ? [...ids, item.id] : ids.filter(id => id !== item.id))} />{item.text}</label>)}</fieldset>}
          <button className="workspace-button workspace-primary" disabled={busy || !actual.trim() || !verdict || (verdict === "passed" && !allVerified)}>{busy ? "Saving…" : "Save manual result"}</button>
        </form> : <p role="status">{state.reason || "Review and approve a test design before recording results."}</p>}
        <section><h3 className="font-semibold">Attempt history</h3><p className="workspace-metadata">Human-reported results are not automation verification. Earlier versions remain historical evidence.</p>
          {!state.records.length && <p>No attempts recorded on this page.</p>}
          {state.records.map(result => <details className="manual-attempt" key={result.run_id}><summary><DesignBadge>{labels[result.verdict]}</DesignBadge> · {result.mode} · {new Date(result.recorded_at).toLocaleString()}</summary>
            <p className="whitespace-pre-wrap">Actual result: {result.actual_result}</p><p>Executed by {result.executor_display_name || "Name not recorded"} · {result.lifecycle}</p>{result.specification.approved_by && <p>Specification approved by {result.specification.approved_by_display_name || "Project member"}{result.specification.approved_at ? ` · ${new Date(result.specification.approved_at).toLocaleString()}` : ""}</p>}<p>Environment: {result.environment?.name || "Not specified"}</p>
            <ol className="list-decimal pl-6">{result.specification.case.procedure.map((step, i) => <li key={i}>{step.instruction} — Expected: {step.expected}</li>)}</ol>
            {result.verdict === "failed" && <AttemptBugPanel projectId={projectId} runId={result.run_id} />}
          </details>)}
          <nav className="design-pagination" aria-label="Attempt history pages"><button type="button" className="workspace-button" disabled={busy || skip === 0} onClick={() => historyPage(skip - 20)}>Previous attempts</button><span>Page {skip / 20 + 1}</span><button type="button" className="workspace-button" disabled={busy || !state.has_more} onClick={() => historyPage(skip + 20)}>Next attempts</button></nav>
        </section>
      </>}
    </div>
  </WorkspaceDialog>;
}
