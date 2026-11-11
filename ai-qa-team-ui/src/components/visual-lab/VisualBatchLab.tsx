"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { CaseResult, VisualBatchRun, VisualBatchStart } from "@/types/visual-batch.generated";
import { apiFetch } from "@/utils/api";
import LabScreenshot from "./LabScreenshot";
import StartupEvidence from "./StartupEvidence";
import PreparationEvidence from "./PreparationEvidence";

const live = (state: string) => ["queued", "starting", "running", "stopping"].includes(state);
const label = (state: string) => state.replaceAll("_", " ");
type Attempt = { key: string; count: number };

function CaseEvidence({ item, base }: { item: CaseResult; base: string }) {
  const [open, setOpen] = useState(false);
  const screenshots = item.screenshots ?? [];
  return <div className="space-y-3">
    {item.state === "completed" && !item.evidence_complete && <p className="text-sm text-amber-700">Evidence incomplete. Completion does not guarantee all screenshots are available.</p>}
    <button type="button" className="rounded-lg border px-3 py-1 text-sm" aria-expanded={open}
      aria-controls={`evidence-${item.case_run_id}`} onClick={() => setOpen(value => !value)}>{open ? "Hide evidence" : "View evidence"}</button>
    {open && <div id={`evidence-${item.case_run_id}`} className="space-y-3">
      <p className="text-xs break-all">Case run: {item.case_run_id}</p>
      {item.started_at && <p className="text-sm">Started {new Date(item.started_at).toLocaleString()}</p>}
      {item.finished_at && <p className="text-sm">Finished {new Date(item.finished_at).toLocaleString()}</p>}
      <ol aria-label="Sanitized case diagnostics" className="space-y-1 text-sm">{(item.logs ?? []).map((line, index) => <li key={index}>{line}</li>)}</ol>
      {item.diagnostic_code && <p className="text-sm">Diagnostic code: {item.diagnostic_code}</p>}
      <PreparationEvidence diagnostics={item.preparation} />
      <StartupEvidence stage={item.startup_stage} reason={item.startup_reason}
        timings={item.startup_timings_ms} diagnostics={item.startup_diagnostics} />
      <div className="grid gap-3 lg:grid-cols-3">{screenshots.map(name => <LabScreenshot key={name} label={name}
        url={`${base}/cases/${item.case_run_id}/artifacts/${name}`} />)}</div>
      {!screenshots.length && <p className="text-sm">No screenshots recorded for this check yet.</p>}
    </div>}
  </div>;
}

export default function VisualBatchLab({ projectId, memberId, base }: { projectId: string; memberId: string; base: string }) {
  const [batches, setBatches] = useState<VisualBatchRun[]>([]);
  const [count, setCount] = useState(2);
  const [pending, setPending] = useState(false);
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [error, setError] = useState("");
  const [loadError, setLoadError] = useState("");
  const [loaded, setLoaded] = useState(false);
  const busy = useRef(false);
  const request = useRef<AbortController | null>(null);
  const submitRequest = useRef<AbortController | null>(null);
  const storageKey = `visual-batch-pending:${encodeURIComponent(memberId)}:${projectId}`;
  const endpoint = `${base}/batches`;

  const refresh = useCallback(async (force = false) => {
    if (request.current && !request.current.signal.aborted && !force) return;
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    try {
      const response = await apiFetch(endpoint, { cache: "no-store", signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]) });
      if (controller.signal.aborted) return;
      if (!response.ok || !Array.isArray(response.data)) throw new Error("Unavailable");
      const rows = response.data as VisualBatchRun[];
      if (rows.some(row => row.schema_version !== "1.0" || row.project_id !== projectId || !Array.isArray(row.cases))) throw new Error("Unsupported response");
      setBatches(rows); setLoaded(true); setLoadError("");
    } catch {
      if (!controller.signal.aborted) { setLoaded(true); setLoadError("Unable to load batches. Check project access, development flags and backend connectivity, then refresh."); }
    } finally { if (request.current === controller) request.current = null; }
  }, [endpoint, projectId]);

  useEffect(() => {
    // Restore an external session record after hydration; never resubmit automatically.
    try {
      const stored = sessionStorage.getItem(storageKey);
      if (stored) {
        const saved = JSON.parse(stored) as Attempt;
        if (/^[0-9a-f]{32}$/.test(saved.key) && Number.isInteger(saved.count) && saved.count >= 1 && saved.count <= 10) {
          setAttempt(saved); setCount(saved.count);
        }
      }
    } catch { /* Unavailable storage or invalid local recovery data is never submitted. */ }
    void refresh();
    return () => { request.current?.abort(); submitRequest.current?.abort(); };
  }, [refresh, storageKey]);

  const hasLive = batches.some(batch => live(batch.state));
  useEffect(() => {
    const visibleRefresh = () => { if (document.visibilityState === "visible") void refresh(); };
    document.addEventListener("visibilitychange", visibleRefresh);
    const timer = hasLive ? setInterval(visibleRefresh, 2000) : undefined;
    return () => { if (timer) clearInterval(timer); document.removeEventListener("visibilitychange", visibleRefresh); };
  }, [hasLive, refresh]);

  async function start() {
    if (busy.current) return;
    busy.current = true; setPending(true); setError("");
    const submission = attempt ?? { key: Array.from(crypto.getRandomValues(new Uint8Array(16)), value => value.toString(16).padStart(2, "0")).join(""), count };
    setAttempt(submission);
    try { sessionStorage.setItem(storageKey, JSON.stringify(submission)); } catch { /* In-memory key still protects this mounted attempt. */ }
    const controller = new AbortController();
    submitRequest.current = controller;
    const body: VisualBatchStart = { schema_version: "1.0", idempotency_key: submission.key, case_count: submission.count };
    try {
      const response = await apiFetch(endpoint, { method: "POST", body: JSON.stringify(body), signal: AbortSignal.any([controller.signal, AbortSignal.timeout(20000)]) });
      if (controller.signal.aborted) return;
      if (!response.ok) {
        setError(response.status === 403 || response.status === 404
          ? "Batch request unavailable. Check your project access and development flags. The same submission key is retained."
          : "Batch request could not be confirmed. Refresh history or resolve the same submission; do not create a replacement.");
        return;
      }
      const run = response.data as VisualBatchRun;
      if (!run?.batch_id || run.project_id !== projectId || run.schema_version !== "1.0") throw new Error("Invalid response");
      setBatches(previous => [run, ...previous.filter(batch => batch.batch_id !== run.batch_id)]);
      setAttempt(null);
      try { sessionStorage.removeItem(storageKey); } catch { /* No secret data stored. */ }
      await refresh(true);
    } catch {
      if (!controller.signal.aborted) setError("Submission outcome is unknown. Refresh history, then resolve the same submission if needed. No automatic retry was made.");
    } finally { busy.current = false; setPending(false); }
  }

  async function cancel(batchId: string) {
    if (busy.current) return;
    busy.current = true; setPending(true); setError("");
    const controller = new AbortController();
    submitRequest.current = controller;
    try {
      const response = await apiFetch(`${endpoint}/${batchId}/cancel`, { method: "POST", signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]) });
      if (!response.ok) { setError("Cancellation could not be confirmed. Refresh the batch status before taking further action."); return; }
      const run = response.data as VisualBatchRun;
      if (!controller.signal.aborted && run?.batch_id === batchId && run.project_id === projectId) {
        setBatches(previous => previous.map(batch => batch.batch_id === batchId ? run : batch));
        await refresh(true);
      }
    } catch { if (!controller.signal.aborted) setError("Cancellation outcome is unknown. Refresh status; the other batch is unaffected."); }
    finally { busy.current = false; setPending(false); }
  }

  return <section aria-label="Synthetic batch execution" className="space-y-5">
    <div className="rounded-xl border p-5 space-y-4">
      <div><h2 className="text-xl font-semibold">Linux smoke batches</h2><p className="text-sm mt-1">Controlled synthetic sample • Headless Chrome • Unbilled development</p></div>
      <p>Run 1–10 repetitions of the synthetic form check per batch. Each check runs in its own isolated container. Checks within and across batches share the configured concurrency pool; checks beyond available account/project capacity queue.</p>
      <p className="text-sm">Customer application execution is unavailable. Your onboarding URL is not used. These checks do not execute generated business tests or evaluate AI assertions.</p>
      <div className="flex flex-wrap items-end gap-4">
        <label className="grid gap-1 text-sm">Number of synthetic checks
          <select className="rounded-lg border px-3 py-2" value={count} disabled={pending || attempt !== null} onChange={event => setCount(Number(event.target.value))}>
            {Array.from({ length: 10 }, (_, index) => <option key={index + 1} value={index + 1}>{index + 1}</option>)}
          </select>
        </label>
        <button type="button" className="rounded-lg bg-indigo-600 text-white px-4 py-2 disabled:opacity-50" disabled={pending} onClick={() => void start()}>
          {pending ? "Request in progress…" : attempt ? "Resolve submitted batch" : "Start synthetic batch"}
        </button>
        <button type="button" className="rounded-lg border px-4 py-2" onClick={() => void refresh(true)}>Refresh batches</button>
      </div>
      {attempt && <p role="status" className="text-sm">A submission is awaiting confirmation. Resolving uses its original idempotency key; it does not create a replacement batch.</p>}
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      {loadError && <p role="alert" className="text-sm text-red-700">{loadError}</p>}
      <p className="text-sm">This project: {batches.filter(batch => ["starting", "running", "stopping"].includes(batch.state)).length} active, {batches.filter(batch => batch.state === "queued").length} queued. Other projects may occupy the global slots.</p>
    </div>
    {!loaded && <p role="status">Loading batch history…</p>}
    {loaded && !loadError && !batches.length && <p>No synthetic batches yet.</p>}
    {batches.length > 0 && <p className="text-sm">Showing the latest {batches.length} project batches (up to 20).</p>}
    {batches.map(batch => <article key={batch.batch_id} aria-label={`Batch ${batch.batch_id}`} className="rounded-xl border p-5 space-y-4">
      <div className="flex flex-wrap justify-between items-start gap-3">
        <div><h3 className="font-semibold">{batch.state === "completed" ? "Browser smoke check completed" : `Batch: ${label(batch.state)}`}</h3>
          <p className="text-sm">{batch.cases.filter(item => item.state === "completed").length}/{batch.cases.length} checks completed • {new Date(batch.created_at).toLocaleString()}</p>
          <p className="text-sm">{batch.execution_strategy === "parallel-checks-v1" ? "Parallel check pool" : "Legacy sequential batch"} • {batch.cases.filter(item => ["starting", "running", "stopping"].includes(item.state ?? "queued")).length} checks active • {batch.cases.filter(item => item.state === "queued").length} checks queued</p>
          <p className="text-xs break-all">Batch {batch.batch_id}</p>
        </div>
        {live(batch.state) && <button type="button" className="rounded-lg border px-4 py-2 disabled:opacity-50" disabled={pending || batch.state === "stopping"}
          onClick={() => void cancel(batch.batch_id)}>{batch.state === "stopping" ? "Cancellation requested" : "Cancel batch"}</button>}
      </div>
      {batch.state === "queued" && <p role="status" className="text-sm">Waiting for available execution capacity.</p>}
      {batch.diagnostic_code && <p className="text-sm">Diagnostic code: {batch.diagnostic_code}</p>}
      <ol aria-label="Checks in batch" className="divide-y rounded-lg border px-4">{batch.cases.map((item, index) => <li key={item.case_run_id} className="py-4 space-y-2">
        <h4 className="font-medium">Check {index + 1} — {label(item.state ?? "queued")}</h4>
        {!["queued", "not_executed"].includes(item.state ?? "queued") && <CaseEvidence item={item} base={`${endpoint}/${batch.batch_id}`} />}
      </li>)}</ol>
      <p className="text-xs">Mechanical execution only. Completed checks are not business test passes. Completed evidence is retained when remaining checks are cancelled or interrupted.</p>
    </article>)}
  </section>;
}
