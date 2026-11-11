"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/utils/api";
import VisualStepEditor, { type AuthoredStep, type WorkflowVersion } from "./VisualStepEditor";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";

interface SpecVersion { version_id: string; status: string; steps: AuthoredStep[]; story_id: string; acceptance_criteria_snapshot: string }
interface SpecState { version: SpecVersion | null; review_required: boolean; reason?: string | null }
interface EnvironmentChoice { env_id: string; env_type: string; credentials: { role: string }[] }
interface Preview { target_url: string; requires_credentials: boolean; environment_revision: number; steps: AuthoredStep[]; execution_ready: false; manifest_digest: string }
interface PreparedRun { run_id: string; state: string; manifest_digest: string; reason: string | null; execution_ready: false }

function SavedSteps({ steps }: { steps: AuthoredStep[] }) {
  return <details><summary>Review saved steps</summary><ol className="list-decimal pl-6">
    {steps.map((step, index) => <li key={index}>
      {step.action} {step.target || step.path || step.expected || step.workflow_version_id}
      {step.value && <span> · {step.value.source === "credential" ? `Selected role’s ${step.value.field}` : step.value.source === "parameter" ? `Input ${step.value.name}` : step.value.text}</span>}
      {Object.entries(step.inputs || {}).map(([name, input]) => <p key={name}>{name} — {input.source === "credential" ? `Selected role’s ${input.field}` : input.text}</p>)}
    </li>)}
  </ol></details>;
}

export default function VisualSpecificationPanel({ projectId, testcaseId, canApprove }: {
  projectId: string; testcaseId?: string; canApprove: boolean;
}) {
  const [open, setOpen] = useState(false);
  return <details className="border rounded p-3" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary className="cursor-pointer font-medium">{testcaseId ? "Visual execution specification" : "Reusable steps library"}</summary>
    {open && <AuthoringForm key={projectId + (testcaseId || "library")} projectId={projectId} testcaseId={testcaseId} canApprove={canApprove} />}
  </details>;
}

function AuthoringForm({ projectId, testcaseId, canApprove }: { projectId: string; testcaseId?: string; canApprove: boolean }) {
  const { enabled } = useFeatures();
  const base = `/projects/${encodeURIComponent(projectId)}/visual-specifications`;
  const casePath = `${base}/cases/${encodeURIComponent(testcaseId || "")}`;
  const [workflows, setWorkflows] = useState<WorkflowVersion[]>([]);
  const [state, setState] = useState<SpecState | null>(null);
  const [environments, setEnvironments] = useState<EnvironmentChoice[]>([]);
  const [environment, setEnvironment] = useState("");
  const [role, setRole] = useState("");
  const [title, setTitle] = useState("");
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const [steps, setSteps] = useState<AuthoredStep[]>([{ action: "assert_text", expected: "" }]);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [admission, setAdmission] = useState<PreparedRun | null>(null);
  const [admissionKey, setAdmissionKey] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    const [response, specification, savedEnvironments] = await Promise.all([
      apiFetch(`${base}/workflows`, { signal }),
      testcaseId ? apiFetch(casePath, { signal }) : Promise.resolve(null),
      testcaseId ? apiFetch(`/environments?project_id=${encodeURIComponent(projectId)}`, { signal }) : Promise.resolve(null),
    ]);
    if (!response.ok || !Array.isArray(response.data)) throw new Error("Could not load reusable workflows.");
    if (testcaseId && (!specification?.ok || !savedEnvironments?.ok || !Array.isArray(savedEnvironments.data))) {
      throw new Error("Could not load specification or environments.");
    }
    if (!signal?.aborted) {
      setWorkflows(response.data);
      if (specification && savedEnvironments) { setState(specification.data); setEnvironments(savedEnvironments.data); }
    }
  }, [base, casePath, projectId, testcaseId]);

  useEffect(() => {
    const controller = new AbortController();
    const reload = () => {
      void load(controller.signal).catch(() => { if (!controller.signal.aborted) setError("Could not load authoring data. Close and reopen to retry."); });
    };
    const refresh = () => { setPreview(null); reload(); };
    reload();
    const eventName = `visual-workflows-updated:${projectId}`;
    if (testcaseId) window.addEventListener(eventName, refresh);
    return () => { controller.abort(); window.removeEventListener(eventName, refresh); };
  }, [load, projectId, testcaseId]);

  async function perform(path: string, body?: object) {
    setBusy(true); setError(""); setPreview(null);
    try {
      const response = await apiFetch(path, { method: "POST", ...(body ? { body: JSON.stringify(body) } : {}) });
      if (!response.ok) throw new Error(typeof response.data?.detail === "string" ? response.data.detail : "Check the step fields and input references.");
      await load();
      if (!testcaseId && path.endsWith("/approve")) window.dispatchEvent(new Event(`visual-workflows-updated:${projectId}`));
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Could not save specification."); }
    finally { setBusy(false); }
  }

  async function previewSpecification() {
    if (!state?.version) return;
    setBusy(true); setError(""); setPreview(null);
    try {
      const response = await apiFetch(`${casePath}/${state.version.version_id}/preview`, {
        method: "POST", body: JSON.stringify({ environment_id: environment, application_role: role || null }),
      });
      if (!response.ok) throw new Error(typeof response.data?.detail === "string" ? response.data.detail : "Could not preview specification.");
      setPreview(response.data);
      setAdmissionKey(crypto.randomUUID().replaceAll("-", ""));
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Could not preview specification."); }
    finally { setBusy(false); }
  }

  async function saveAdmission(cancel = false) {
    if (!state?.version || (!cancel && (!preview || !admissionKey))) return;
    setBusy(true); setError("");
    try {
      const path = cancel ? `${base}/runs/${admission?.run_id}/cancel` : `${casePath}/${state.version.version_id}/runs`;
      const response = await apiFetch(path, { method: "POST", body: JSON.stringify(cancel ? {} : {
        environment_id: environment, application_role: role || null,
        preview_digest: preview?.manifest_digest, idempotency_key: admissionKey,
      }) });
      if (!response.ok) throw new Error(typeof response.data?.detail === "string" ? response.data.detail : "Could not save run admission.");
      setAdmission(response.data);
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Could not save run admission."); }
    finally { setBusy(false); }
  }

  return <div className="mt-4 space-y-4">
    <p>Author and approve bounded steps. Browser execution remains pending hosting, targeting and network qualification.</p>
    {error && <p role="alert">{error}</p>}
    {!testcaseId && <label>Workflow title <input className="workspace-input" value={title} onChange={event => setTitle(event.target.value)} /></label>}
    <VisualStepEditor steps={steps} onChange={setSteps} workflows={workflows} reusable={!testcaseId} />
    <button className="workspace-button" disabled={busy || !steps.length || (!testcaseId && !title.trim())}
      onClick={() => void perform(testcaseId ? casePath : `${base}/workflows`, testcaseId ? { steps } : { title, steps, ...(workflowId ? { workflow_id: workflowId } : {}) })}>Save new draft version</button>
    {!testcaseId && <>
      <button className="workspace-button" onClick={() => { setWorkflowId(null); setTitle(""); setSteps([{ action: "assert_text", expected: "" }]); }}>Start a new workflow</button>
      {workflows.map(workflow => <div className="border rounded p-3" key={workflow.version_id}>
        <p>{workflow.title} · {workflow.status} · {workflow.version_id.slice(0, 8)}</p>
        <SavedSteps steps={workflow.steps} />
        <button disabled={busy} onClick={() => { setWorkflowId(workflow.workflow_id); setTitle(workflow.title); setSteps(workflow.steps); }}>Use as successor draft</button>
        {canApprove && workflow.status === "draft" && <button className="workspace-button" disabled={busy} onClick={() => void perform(`${base}/workflows/${workflow.version_id}/approve`)}>Approve workflow version</button>}
      </div>)}
    </>}
    {testcaseId && state?.version && <div className="space-y-3">
      <p role="status">{state.version.status} · {state.review_required ? "Review required" : "Current approval"} · {state.version.version_id.slice(0, 8)}</p>
      <p>Source story {state.version.story_id}</p>
      <details><summary>Acceptance criteria snapshot</summary><p>{state.version.acceptance_criteria_snapshot}</p></details>
      <SavedSteps steps={state.version.steps} />
      {state.reason && <p>{state.reason}</p>}
      <button disabled={busy} onClick={() => setSteps(state.version?.steps || [])}>Load saved steps as successor draft</button>
      {canApprove && state.version.status === "draft" && <button className="workspace-button" disabled={busy} onClick={() => void perform(`${casePath}/${state.version?.version_id}/approve`)}>Approve specification version</button>}
      <label className="block">Environment <select value={environment} onChange={event => { setEnvironment(event.target.value); setRole(""); setPreview(null); }}>
        <option value="">Choose environment</option>{environments.map(item => <option key={item.env_id} value={item.env_id}>{item.env_type} ({item.env_id})</option>)}
      </select></label>
      <label className="block">Application role <select value={role} onChange={event => { setRole(event.target.value); setPreview(null); }}>
        <option value="">No credentials</option>{environments.find(item => item.env_id === environment)?.credentials.map(item => <option key={item.role} value={item.role}>{item.role}</option>)}
      </select></label>
      <button className="workspace-button" disabled={busy || !environment || state.version.status !== "approved" || state.review_required} onClick={() => void previewSpecification()}>Preview approved steps</button>
    </div>}
    {preview && <div role="status">Prepared preview for {preview.target_url} · environment revision {preview.environment_revision} · {preview.steps.length} expanded steps · {preview.requires_credentials ? "Credential role required" : "Public-page workflow"}. Browser execution pending.</div>}
    {preview && enabled("approved_visual_run_admission") && <button className="workspace-button" disabled={busy || !admissionKey} onClick={() => void saveAdmission()}>Save immutable run admission (no execution)</button>}
    {admission && <div className="border rounded p-3 space-y-2"><p role="status">Run admission {admission.run_id} · {admission.state}. General worker not enabled; no browser has launched.</p>
      <p>Manifest digest: {admission.manifest_digest}</p>
      {admission.state === "prepared" && <button className="workspace-button" disabled={busy} onClick={() => void saveAdmission(true)}>Cancel prepared admission</button>}
    </div>}
  </div>;
}
