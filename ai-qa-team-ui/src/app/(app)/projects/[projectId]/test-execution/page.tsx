"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";
import ApprovedVisualRunPanel from "@/components/visual-lab/ApprovedVisualRunPanel";
import { apiFetch } from "@/utils/api";

type Project = { current_user_role?: string };
type Case = { testcase_id: string; title: string; project_id: string };
type Environment = { env_id: string; project_id: string; name?: string; credentials?: { role: string; password_configured?: boolean }[] };

export default function TestExecutionPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { enabled } = useFeatures();
  const available = enabled("test_execution_ui", "test_generation", "approved_visual_run_admission");
  const [data, setData] = useState<{project: Project; cases: Case[]; environments: Environment[]} | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!available) return;
    const controller = new AbortController();
    const id = encodeURIComponent(projectId);
    Promise.all([`/projects/${id}`, `/testcases/testcases?project_id=${id}`, `/environments?project_id=${id}`].map(path => apiFetch(path, { signal: controller.signal }))).then(([project, cases, environments]) => {
      if (!project.ok || !cases.ok || !environments.ok || !Array.isArray(cases.data) || !Array.isArray(environments.data)) throw new Error("LOAD_FAILED");
      if (!controller.signal.aborted) setData({project: project.data, cases: cases.data.filter((item: Case) => item.project_id === projectId), environments: environments.data.filter((item: Environment) => item.project_id === projectId)});
    }).catch(() => { if (!controller.signal.aborted) setError("Could not load test execution. Reload to try again."); });
    return () => controller.abort();
  }, [available, projectId]);
  if (!available) return <p role="status">Test execution is currently hidden.</p>;
  return <div className="design-page"><header><h1>Test Execution</h1><p>Review approved specifications before starting an explicitly enabled development run.</p></header>{error ? <p role="alert">{error}</p> : !data ? <p role="status">Loading test execution…</p> : <ApprovedVisualRunPanel key={projectId} projectId={projectId} cases={data.cases} environments={data.environments} canApprove={data.project.current_user_role === "ADMIN"} />}</div>;
}
