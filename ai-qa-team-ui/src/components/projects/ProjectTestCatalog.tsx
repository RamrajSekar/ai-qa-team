"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { apiFetch } from "@/utils/api";
import type { Scenario } from "@/types/scenario";
import { useProjects } from "@/hooks/useProjects";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";
import VisualSpecificationPanel from "@/components/visual-lab/VisualSpecificationPanel";
import { useAuth } from "@/components/providers/AuthProvider";
import ScenarioModal from "@/components/scenarios/ScenarioModal";
import TestCaseEditor from "@/components/projects/TestCaseEditor";
import CatalogCreation from "./CatalogCreation";
import ScenarioViewer from "@/components/scenarios/ScenarioViewer";
import TestDesignReview from "./TestDesignReview";

export interface CatalogCase {
  updated_at?: string;
  created_by?: string;
  testcase_id: string;
  scenario_id: string;
  title: string;
  description?: string;
  complexity?: string;
  status: string;
  purpose?: string;
  role?: string | null;
  preconditions?: string[];
  public_data?: Record<string, string>;
  assertions?: string[];
  cleanup?: string[];
  knowledge_version_id?: string;
  acceptance_criteria_refs?: string[];
  rule_references?: string[];
  steps: { description?: string; action: string; expected?: string | null }[];
}

export default function ProjectTestCatalog({ kind }: { kind: "scenarios" | "testcases" }) {
  const { projectId } = useParams<{ projectId: string }>();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [cases, setCases] = useState<CatalogCase[]>([]);
  const { user } = useAuth();
  const { enabled } = useFeatures();
  const { projects } = useProjects();
  const canApprove = projects.find(project => project.project_id === projectId)?.current_user_role === "ADMIN";
  const [editingScenario, setEditingScenario] = useState<Scenario | null>(null);
  const [editingCase, setEditingCase] = useState<CatalogCase | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [actionError, setActionError] = useState("");
  const [selected, setSelected] = useState<Scenario | null>(null);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const title = kind === "scenarios" ? "Scenarios" : "Test Cases";

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    try {
      const response = await apiFetch(`/${kind}/project-list?project_id=${encodeURIComponent(projectId)}&skip=${page * 50}&limit=50`, { signal });
      if (!response.ok || !Array.isArray(response.data)) {
        throw new Error(`Could not load ${kind === "scenarios" ? "scenarios" : "test cases"} (HTTP ${response.status}).`);
      }
      if (signal?.aborted) return;
      if (kind === "scenarios") setScenarios(response.data);
      else setCases(response.data);
    } catch (failure) {
      if (!signal?.aborted) setError(failure instanceof Error ? failure.message : "Could not load records.");
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [kind, page, projectId]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  async function removeRecord(id: string) {
    if (!window.confirm("Delete this record? Records with dependent tests, approvals or execution history are protected.")) return;
    setDeleting(true);
    setActionError("");
    try {
      const response = await apiFetch(`/${kind}/${encodeURIComponent(id)}?project_id=${encodeURIComponent(projectId)}`, { method: "DELETE" });
      if (!response.ok) throw new Error(typeof response.data?.detail === "string" ? response.data.detail : "Could not delete record.");
      await load();
    } catch (failure) {
      setActionError(failure instanceof Error ? failure.message : "Could not delete record.");
    } finally { setDeleting(false); }
  }

  const count = kind === "scenarios" ? scenarios.length : cases.length;
  const projectPath = `/projects/${encodeURIComponent(projectId)}`;
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">{title}</h1>
        <Link className="workspace-button" href={`${projectPath}/stories`}>Open stories to create or generate</Link>
      </div>
      {kind === "testcases" && enabled("reusable_workflows") && <VisualSpecificationPanel projectId={projectId} canApprove={canApprove} />}
      <CatalogCreation key={projectId} kind={kind} projectId={projectId} onSaved={async () => { await load(); }} />
      {actionError && <p role="alert">{actionError}</p>}
      {loading ? <p role="status">Loading {title.toLowerCase()}…</p> : error ? (
        <div role="alert"><p>{error}</p><button className="workspace-button" onClick={() => void load()}>Try again</button></div>
      ) : <>
        {count === 0 && <p>No {title.toLowerCase()} on this page. Create a scenario from a story, then approve it to generate test cases.</p>}
        {kind === "scenarios" ? scenarios.map(scenario => (
          <article className="border rounded-lg bg-white p-4 space-y-2" key={scenario.scenario_id}>
            <h2 className="font-semibold">{scenario.title}</h2>
            <p>{scenario.scenario_id} · {scenario.approved ? "Approved" : "Pending approval"}</p>
            <div className="flex gap-4">
              <Link href={`${projectPath}/stories/${encodeURIComponent(scenario.story_id)}`}>Story {scenario.story_id}</Link>
              <button className="workspace-button" onClick={() => setSelected(scenario)}>Review scenario</button>
              {scenario.created_by === user?.email && <>
                <button className="workspace-button" onClick={() => setEditingScenario(scenario)}>Edit scenario</button>
                <button className="workspace-button" disabled={deleting} onClick={() => void removeRecord(scenario.scenario_id)}>Delete scenario</button>
              </>}
            </div>
          </article>
        )) : cases.map(testcase => (
          <article className="border rounded-lg bg-white p-4 space-y-2" key={testcase.testcase_id}>
            <h2 className="font-semibold">{testcase.title}</h2>
            <p>{testcase.testcase_id} · {testcase.complexity || "Unspecified complexity"} · {testcase.status}</p>
            {testcase.description && <p>{testcase.description}</p>}
            {enabled("product_knowledge", "story_analysis") && <TestDesignReview key={`${testcase.testcase_id}:${testcase.updated_at || ""}`} testcase={testcase} projectId={projectId} canApprove={canApprove} />}
            {testcase.knowledge_version_id && <details><summary>Purpose, data and approved context</summary>
              <p>Purpose: {testcase.purpose}</p><p>Role: {testcase.role || "Not specified"}</p>
              <p>Preconditions: {testcase.preconditions?.join("; ")}</p>
              <p>Public data: {Object.entries(testcase.public_data || {}).map(([key, value]) => `${key}: ${value}`).join("; ")}</p>
              <p>Required assertions: {testcase.assertions?.join("; ")}</p><p>Cleanup: {testcase.cleanup?.join("; ") || "None specified"}</p>
              <p>Acceptance criteria: {testcase.acceptance_criteria_refs?.join("; ")}</p>
              <p>Rules: {testcase.rule_references?.join(", ") || "Reviewer-authored acceptance criteria"}</p>
              <p>Knowledge version: {testcase.knowledge_version_id}</p>
            </details>}
            {enabled("reusable_workflows") && <VisualSpecificationPanel key={`${testcase.testcase_id}:${testcase.updated_at || ""}`} projectId={projectId} testcaseId={testcase.testcase_id} canApprove={canApprove} />}
            <details><summary className="cursor-pointer">Steps and expected results</summary>
              <ol className="list-decimal pl-6 space-y-2 mt-3">
                {testcase.steps.map((step, index) => <li key={index}>
                  <p>{step.description || step.action}</p>
                  <p className="text-sm text-gray-600">Expected result — {step.expected || "No explicit expected result recorded"}</p>
                </li>)}
              </ol>
            </details>
            <div className="flex gap-4">
              <Link href={`${projectPath}/scenarios`}>Source scenario {testcase.scenario_id}</Link>
              <Link href={projectPath}>Review execution approval on overview</Link>
              {testcase.created_by === user?.email && <>
                <button className="workspace-button" onClick={() => setEditingCase(testcase)}>Edit test case</button>
                <button className="workspace-button" disabled={deleting} onClick={() => void removeRecord(testcase.testcase_id)}>Delete test case</button>
              </>}
            </div>
          </article>
        ))}
        <div className="flex items-center gap-4">
          <button className="workspace-button" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button>
          <span>Page {page + 1}</span>
          <button className="workspace-button" disabled={count < 50} onClick={() => setPage(page + 1)}>Next</button>
        </div>
      </>}
      {editingScenario && <ScenarioModal key={editingScenario.scenario_id} open scenario={editingScenario}
        projectId={projectId} storyId={editingScenario.story_id} onClose={() => setEditingScenario(null)}
        onSaved={async () => { await load(); }} />}
      {editingCase && <TestCaseEditor testcase={editingCase} projectId={projectId}
        onClose={() => setEditingCase(null)} onSaved={async () => { setEditingCase(null); await load(); }} />}
      <ScenarioViewer key={selected?.scenario_id || "closed"} open={!!selected} scenario={selected}
        onClose={() => setSelected(null)} onApproved={scenario => {
          setSelected(scenario);
          setScenarios(rows => rows.map(row => row.scenario_id === scenario.scenario_id ? scenario : row));
        }} />
    </div>
  );
}
