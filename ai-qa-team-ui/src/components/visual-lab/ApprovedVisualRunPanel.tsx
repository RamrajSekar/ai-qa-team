"use client";

import { useEffect, useState, type FormEvent } from "react";
import { apiFetch } from "@/utils/api";
import StagingBindingPanel from "./StagingBindingPanel";
import LabScreenshot from "./LabScreenshot";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";

type Testcase = { testcase_id: string; title: string };
type Environment = {
  env_id?: string; name?: string; env_type?: string;
  credentials?: { role: string; password_configured?: boolean }[];
};
type Approval = { version_id: string; story_id: string; button_label: string; expected_text: string };
type Preview = { preview_digest: string; environment_id: string; test: Approval };
type Run = Preview & {
  run_id: string;
  state: "admitted" | "running" | "cancelling" | "completed" | "cancelled";
  verdict?: "passed" | "failed" | "blocked" | "needs_review" | "cancelled" | null;
  observed_text?: string | null;
  evidence_available?: boolean;
  reason?: string | null;
};
type CaseState = { approval: Approval | null; latest_run: Run | null };
const verdictLabels = { passed: "Passed", failed: "Failed", blocked: "Blocked", needs_review: "Needs review", cancelled: "Cancelled" };

export default function ApprovedVisualRunPanel({ projectId, cases, environments, canApprove }: {
  projectId: string; cases: Testcase[]; environments: Environment[]; canApprove: boolean;
}) {
  const { enabled } = useFeatures();
  const executionEnabled = enabled("approved_visual_run_execution");
  const [selected, setSelected] = useState("");
  const testcase = cases.find(item => item.testcase_id === selected);
  return (
    <section id="approved-visual-run" className="workspace-panel p-4 space-y-3" aria-label="Approved visual run">
      <h2 className="font-semibold">Approved visual run</h2>
      <p className="text-sm">{executionEnabled
        ? "Development execution uses one BrowserStack session against the controlled sample. Approve “Save draft” and “Draft saved” for the positive check."
        : "Development admission only. The target is the controlled sample. Admitting a request does not start a browser."}</p>
      <label className="block">
        Test case{" "}
        <select className="workspace-input" value={testcase?.testcase_id ?? ""} onChange={event => setSelected(event.target.value)}>
          <option value="">Select a test case</option>
          {cases.map(item => <option key={item.testcase_id} value={item.testcase_id}>{item.title}</option>)}
        </select>
      </label>
      {testcase && <RunControls key={testcase.testcase_id} projectId={projectId} testcaseId={testcase.testcase_id}
        environments={environments} canApprove={canApprove} executionEnabled={executionEnabled} />}
    </section>
  );
}

function RunControls({ projectId, testcaseId, environments, canApprove, executionEnabled }: {
  projectId: string; testcaseId: string; environments: Environment[]; canApprove: boolean; executionEnabled: boolean;
}) {
  const base = `/projects/${encodeURIComponent(projectId)}/approved-visual-runs`;
  const testcasePath = `${base}/testcases/${encodeURIComponent(testcaseId)}`;
  const [approval, setApproval] = useState<Approval | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [label, setLabel] = useState("");
  const [expected, setExpected] = useState("");
  const [environment, setEnvironment] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [requestKey, setRequestKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    apiFetch(testcasePath, { signal: controller.signal, cache: "no-store" }).then(response => {
      if (controller.signal.aborted) return;
      if (!response.ok) throw new Error("The test case approval could not be loaded.");
      const state: CaseState = response.data;
      setApproval(state.approval);
      setLabel(state.approval?.button_label ?? "");
      setExpected(state.approval?.expected_text ?? "");
      setRun(state.latest_run);
      setLoaded(true);
    }).catch(() => {
      if (!controller.signal.aborted) setError("The test case approval could not be loaded. Reselect the test case to retry.");
    });
    return () => controller.abort();
  }, [testcasePath]);

  async function perform(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "The request could not be completed.");
    } finally {
      setBusy(false);
    }
  }

  async function request<T>(path: string, method: "GET" | "POST", body?: object): Promise<T> {
    const response = await apiFetch(path, {
      method, cache: "no-store", signal: AbortSignal.timeout(15000),
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    if (!response.ok) {
      const detail = response.data?.detail;
      throw new Error(typeof detail === "string" ? detail : `Request rejected (${response.status}).`);
    }
    return response.data;
  }

  function approve(event: FormEvent) {
    event.preventDefault();
    void perform(async () => {
      setPreview(null);
      const approved = await request<Approval>(`${testcasePath}/approve`, "POST", {
        button_label: label.trim(), expected_text: expected.trim(),
      });
      setApproval(approved);
    });
  }

  const selection = approval && environment ? {
    approved_test_version_id: approval.version_id, environment_id: environment,
  } : null;
  const active = run?.state === "admitted" || run?.state === "running" || run?.state === "cancelling";

  return <div className="space-y-3" aria-busy={busy}>
    {error && <p role="alert" className="text-red-700 text-sm">{error}</p>}
    {!loaded && !error && <p role="status">Loading approval and latest run…</p>}
    {loaded && <>
      {canApprove && <form onSubmit={approve} className="space-y-2">
        <label className="block">Visible button label{" "}
          <input className="workspace-input" required maxLength={240} disabled={busy} value={label}
            onChange={event => setLabel(event.target.value)} />
        </label>
        <label className="block">Expected visible text{" "}
          <input className="workspace-input" required maxLength={240} disabled={busy} value={expected}
            onChange={event => setExpected(event.target.value)} />
        </label>
        <button className="workspace-button" type="submit" disabled={busy || !label.trim() || !expected.trim()}>
          Approve synthetic specification
        </button>
      </form>}
      {approval ? <p className="text-sm">Approved version <code>{approval.version_id}</code> · Story {approval.story_id}</p>
        : <p className="text-sm">A project administrator must approve a synthetic specification.</p>}
      {approval && <div className="flex flex-wrap gap-2 items-center">
        <label>Saved environment{" "}
          <select className="workspace-input" value={environment} disabled={busy}
            onChange={event => { setEnvironment(event.target.value); setPreview(null); }}>
            <option value="">Select an environment</option>
            {environments.map(item => item.env_id && <option key={item.env_id} value={item.env_id}>
              {item.name || item.env_type || item.env_id} ({item.env_id})
            </option>)}
          </select>
        </label>
        <button type="button" className="workspace-button" disabled={busy || !selection || active}
          onClick={() => selection && void perform(async () => {
            setPreview(null);
            const result = await request<Preview>(`${base}/preview`, "POST", selection);
            setRequestKey(crypto.randomUUID().replaceAll("-", ""));
            setPreview(result);
          })}>Preview synthetic run</button>
      </div>}
      {preview && <div className="space-y-2">
        <p>Target: Controlled synthetic sample · Environment {preview.environment_id}</p>
        <ol className="list-decimal pl-5">
          <li>Open the controlled sample.</li>
          <li>Locate and click “{preview.test.button_label}”.</li>
          <li>Verify “{preview.test.expected_text}”.</li>
        </ol>
        <button type="button" className="workspace-button workspace-primary" disabled={busy || active}
          onClick={() => selection && void perform(async () => {
            setRun(await request<Run>(base, "POST", {
              ...selection, preview_digest: preview.preview_digest, idempotency_key: requestKey,
            }));
            setPreview(null);
          })}>Admit synthetic run</button>
      </div>}
      {run && <div className="space-y-2">
        <p role="status">{run.verdict ? verdictLabels[run.verdict] : run.state === "admitted"
          ? (executionEnabled ? "Admitted · ready to start" : "Admitted · awaiting execution support")
          : run.state === "cancelling" ? "Cancelling"
          : run.state === "cancelled" ? "Cancelled"
          : run.state === "completed" ? "Completed" : "Running"} · <code className="break-all">{run.run_id}</code></p>
        {run.observed_text && <p>Expected “{run.test.expected_text}” · Observed “{run.observed_text}”</p>}
        {run.reason && <p className="text-sm">Diagnostic: {run.reason}</p>}
        {run.state === "admitted" && executionEnabled && <button type="button" className="workspace-button workspace-primary mr-2" disabled={busy}
          onClick={() => void perform(async () => setRun(await request<Run>(`${base}/${run.run_id}/start`, "POST")))}>Start synthetic browser run</button>}
        <button type="button" className="workspace-button" disabled={busy}
          onClick={() => void perform(async () => setRun(await request<Run>(`${base}/${run.run_id}`, "GET")))}>Refresh status</button>
        {(run.state === "admitted" || run.state === "running") && <button type="button" className="workspace-button ml-2" disabled={busy}
          onClick={() => void perform(async () => setRun(await request<Run>(`${base}/${run.run_id}/cancel`, "POST")))}>
          {run.state === "admitted" ? "Cancel admission" : "Cancel browser run"}
        </button>}
        {run.evidence_available && <LabScreenshot key={run.run_id} url={`${base}/${run.run_id}/evidence`} label="Synthetic run evidence" />}
      </div>}
      {approval && <StagingBindingPanel key={approval.version_id} projectId={projectId} testcaseId={testcaseId}
        approvedVersionId={approval.version_id} environments={environments} />}
    </>}
  </div>;
}
