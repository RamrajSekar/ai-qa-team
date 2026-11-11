"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Screenshot from "@/components/visual-lab/LabScreenshot";
import VisualBatchLab from "@/components/visual-lab/VisualBatchLab";
import { useAuth } from "@/components/providers/AuthProvider";
import { apiFetch } from "@/utils/api";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";

type Run = {
  run_id: string; state: string; headed: boolean; created_at: string;
  logs: string[]; screenshots: string[]; browser_version: string | null; diagnostic_code: string | null;
  startup_stage?: string | null; startup_reason?: string | null;
  startup_timings_ms?: Record<string, number>;
  startup_diagnostics?: {
    driver_version?: string | null; driver_state: string; driver_exit_code?: number | null;
    browser_state: string; devtools_port_file: string; session_created: boolean;
    cleanup: string; cleanup_driver_exit_code?: number | null; cleanup_browser_state: string;
    native_errors: string[];
  } | null;
};
const active = (run?: Run) => !!run && ["starting", "running", "stopping"].includes(run.state);

export default function VisualRunnerLabPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { enabled, ready } = useFeatures();
  const { user } = useAuth();
  const memberId = typeof user?.email === "string" ? user.email.trim().toLowerCase() : "";
  const [runs, setRuns] = useState<Run[]>([]);
  const [headed, setHeaded] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const base = `/projects/${encodeURIComponent(projectId)}/visual-lab`;
  const available = ready && enabled("visual_runner_lab");
  const batchMode = available && enabled("visual_runner_batches");
  const hasActiveSmoke = runs.some(active);
  const refresh = useCallback(async () => {
    try {
    const response = await apiFetch(`${base}/runs`, { cache: "no-store" });
    if (!response.ok) { setError("Unable to load smoke checks. Verify project access and the development flag."); return; }
    setRuns(response.data);
    } catch { setError("The service could not be reached. Status will reconcile after reconnecting."); }
  }, [base]);
  useEffect(() => {
    if (!available) return;
    void refresh();
    const timer = hasActiveSmoke ? setInterval(() => { if (document.visibilityState === "visible") void refresh(); }, 1000) : undefined;
    return () => { if (timer) clearInterval(timer); };
  }, [available, refresh, hasActiveSmoke]);
  async function action(path: string, body?: object) {
    setPending(true); setError("");
    try {
      const response = await apiFetch(`${base}${path}`, { method: "POST", ...(body ? { body: JSON.stringify(body) } : {}) });
      if (!response.ok) {
        const detail = response.data?.detail;
        setError(typeof detail === "string" ? detail : "Smoke check request rejected.");
      }
      await refresh();
    } catch { setError("The service could not be reached. Run status will reconcile after reconnecting."); }
    finally { setPending(false); }
  }
  if (!available) return <p role="status">{ready ? "Visual Runner Lab is disabled." : "Loading features…"}</p>;
  return <div className="space-y-6">
    <div className="workspace-page-header"><div><p className="workspace-eyebrow">Internal development • M1A</p><h1>Visual Runner Lab</h1>
      <p className="workspace-description">A mechanical browser smoke check on a synthetic local sample. Fixture coordinates and keyboard actions only.</p></div></div>
    {batchMode && (memberId ? <VisualBatchLab key={`${projectId}:${memberId}`} projectId={projectId} memberId={memberId} base={base} /> : <p role="status">Sign in to load batch controls.</p>)}
    <section className="rounded-xl border p-5 space-y-4">
      {batchMode && <h2 className="font-semibold">Single smoke history</h2>}
      <p>No AI calls, customer data or business test verdict. A completed check does not establish visual validation or MVP readiness.</p>
      {!batchMode && <><label className="flex gap-2 items-center"><input type="checkbox" checked={headed} disabled={pending || runs.some(active)} onChange={e => setHeaded(e.target.checked)} />Open a visible local browser (new session)</label>
      <button className="rounded-lg bg-indigo-600 text-white px-4 py-2 disabled:opacity-50" disabled={pending || runs.some(active)} onClick={() => void action("/runs", { headed })}>Start browser smoke check</button></>}
      {batchMode && <p className="text-sm">Linux batch mode is enabled. Existing single smoke checks remain available below; new single smoke starts are disabled.</p>}
      <p className="text-sm">Robot → custom Python library → HTTPX WebDriver → ChromeDriver → Chrome for Testing. {batchMode ? "Existing single-smoke history is preserved." : "One browser across local projects."}</p>
      {error && <p role="alert">{error}</p>}
    </section>
    {runs.map(run => <section key={run.run_id} className="rounded-xl border p-5 space-y-4">
      <div className="flex flex-wrap justify-between gap-3"><div><h2 className="font-semibold">{run.state === "completed" ? "Browser smoke check completed" : `Smoke check: ${run.state}`}</h2>
        <p className="text-sm">{run.headed ? "Visible" : "Headless"} session • {new Date(run.created_at).toLocaleString()} {run.browser_version && `• Chrome ${run.browser_version}`}</p><p className="text-xs">{run.run_id}</p></div>
        {active(run) && <button disabled={pending || run.state === "stopping"} className="rounded-lg border px-4 py-2" onClick={() => void action(`/runs/${run.run_id}/cancel`)}>Cancel smoke check</button>}</div>
      <ol aria-label="Sanitized runner diagnostics" className="space-y-1 text-sm">{run.logs.map((line, i) => <li key={i}>{line}</li>)}</ol>
      {run.diagnostic_code && <p className="text-sm">Diagnostic code: {run.diagnostic_code}</p>}
      {run.startup_stage && <p className="text-sm">Startup stage: {run.startup_stage}{run.startup_reason ? ` • ${run.startup_reason}` : ""}</p>}
      {run.startup_diagnostics && <details className="text-sm"><summary>Startup diagnostic bundle</summary>
        <dl className="grid grid-cols-2 gap-2 mt-2">
          <dt>ChromeDriver version</dt><dd>{run.startup_diagnostics.driver_version || "Not available"}</dd>
          <dt>Driver before cleanup</dt><dd>{run.startup_diagnostics.driver_state} {run.startup_diagnostics.driver_exit_code != null && `(exit ${run.startup_diagnostics.driver_exit_code})`}</dd>
          <dt>Browser before cleanup</dt><dd>{run.startup_diagnostics.browser_state}</dd>
          <dt>DevTools port file</dt><dd>{run.startup_diagnostics.devtools_port_file}</dd>
          <dt>Session created</dt><dd>{run.startup_diagnostics.session_created ? "Yes" : "No"}</dd>
          <dt>Cleanup observation</dt><dd>{run.startup_diagnostics.cleanup}</dd>
          <dt>Browser after cleanup</dt><dd>{run.startup_diagnostics.cleanup_browser_state}</dd>
          <dt>Driver cleanup exit code</dt><dd>{run.startup_diagnostics.cleanup_driver_exit_code ?? "Not available"}</dd>
          <dt>Native error categories</dt><dd>{run.startup_diagnostics.native_errors.join(", ") || "None captured (does not establish absence of errors)"}</dd>
        </dl>
        <p className="mt-2">Observations are bounded samples. Not observed does not mean the browser never launched.</p>
        <ul aria-label="Startup stage timings">{Object.entries(run.startup_timings_ms || {}).map(([stage, ms]) => <li key={stage}>{stage}: {ms} ms</li>)}</ul>
      </details>}
      <div className="grid gap-4 lg:grid-cols-3">{run.screenshots.map(name => <Screenshot key={name} label={name} url={`${base}/runs/${run.run_id}/artifacts/${name}`} />)}</div>
    </section>)}
    {!runs.length && <p>No smoke checks yet.</p>}
  </div>;
}
