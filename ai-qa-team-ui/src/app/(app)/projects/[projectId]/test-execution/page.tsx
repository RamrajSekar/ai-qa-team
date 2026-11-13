"use client";

import { Suspense, useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";
import ManualExecutions from "@/components/projects/ManualExecutions";
import VisualSpecificationPanel from "@/components/visual-lab/VisualSpecificationPanel";
import ApprovedVisualRunPanel from "@/components/visual-lab/ApprovedVisualRunPanel";
import Link from "next/link";
import { DesignState, DesignStats } from "@/components/projects/DesignWorkspace";
import { apiFetch } from "@/utils/api";

type Project = { current_user_role?: string };
type Case = { testcase_id: string; title: string; project_id: string };
type Environment = { env_id: string; project_id: string; name?: string; credentials?: { role: string; password_configured?: boolean }[] };

export default function TestExecutionPage() {
  return <Suspense fallback={<p role="status">Loading execution view…</p>}><ExecutionRouter /></Suspense>;
}

function ExecutionRouter() {
  const { enabled } = useFeatures();
  const executionId = useSearchParams().get("execution");
  const { projectId } = useParams<{ projectId: string }>();
  if (enabled("manual_test_results", "test_generation")) return <ManualExecutions key={`${projectId}:${executionId || "list"}`} projectId={projectId} executionId={executionId} />;
  return <ExecutionWorkspace key={projectId} projectId={projectId} />;
}

function ExecutionWorkspace({ projectId }: { projectId: string }) {
  const { enabled } = useFeatures();
  const available = enabled("automation_execution_ui", "test_execution_ui", "test_generation", "approved_visual_run_admission");
  const [data, setData] = useState<{project: Project; cases: Case[]; environments: Environment[]} | null>(null);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    if (!available) return;
    const controller = new AbortController();
    const id = encodeURIComponent(projectId);
    Promise.all([`/projects/${id}`, `/testcases/testcases?project_id=${id}`, `/environments?project_id=${id}`].map(path => apiFetch(path, { signal: AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]) }))).then(([project, cases, environments]) => {
      if (!project.ok || !cases.ok || !environments.ok || !Array.isArray(cases.data) || !Array.isArray(environments.data)) throw new Error("LOAD_FAILED");
      if (!controller.signal.aborted) setData({project: project.data, cases: cases.data.filter((item: Case) => item.project_id === projectId), environments: environments.data.filter((item: Environment) => item.project_id === projectId)});
    }).catch(() => { if (!controller.signal.aborted) setError("Could not load test execution. Check your connection and try again."); });
    return () => controller.abort();
  }, [available, projectId, revision]);
  return <div className="design-page execution-workspace">
    <header className="workspace-page-header"><div><p className="workspace-eyebrow">Controlled execution</p><h1>Test Execution</h1><p className="workspace-description">Select a test case, review the exact specification and inspect evidence.</p></div><Link className="workspace-button" href={`/projects/${encodeURIComponent(projectId)}/execution-history`}>Execution history</Link></header>
    {!available ? <DesignState title="Test execution is currently hidden."><p>Execution requires explicitly enabled development controls. You can continue designing and reviewing test cases.</p><Link className="workspace-button" href={`/projects/${encodeURIComponent(projectId)}/testcases`}>Review test cases</Link></DesignState> : <>
      <div className="design-guide"><strong>Development controls · controlled sample only</strong><p>Approval, admission and browser start are separate actions. A saved environment does not authorize customer-site execution. Review explicit expectations before starting; use the selected case’s status and evidence below.</p></div>
      {error ? <DesignState error title={error}><button className="workspace-button" onClick={() => { setData(null); setError(""); setRevision(value => value + 1); }}>Try again</button></DesignState> : !data ? <DesignState title="Loading test execution…" /> : <>
        {enabled("reusable_workflows") && <VisualSpecificationPanel projectId={projectId} canApprove={data.project.current_user_role === "ADMIN"} />}
        <DesignStats items={[{ label: "Available test cases", value: data.cases.length }, { label: "Saved environments", value: data.environments.length }, { label: "Your review access", value: data.project.current_user_role === "ADMIN" ? "Project admin" : "Project member" }]} />
        {!data.cases.length ? <DesignState title="Add a test case first"><p>Create and review a specification before preparing a development run.</p><Link className="workspace-button" href={`/projects/${encodeURIComponent(projectId)}/testcases`}>Open test cases</Link></DesignState> : <ApprovedVisualRunPanel key={projectId} projectId={projectId} cases={data.cases} environments={data.environments} canApprove={data.project.current_user_role === "ADMIN"} />}
        {!data.environments.length && <DesignState title="No saved environments"><p>Configure an environment before previewing an admission.</p><Link className="workspace-button" href={`/projects/${encodeURIComponent(projectId)}/environments`}>Open environments</Link></DesignState>}
      </>}
    </>}
  </div>;
}
