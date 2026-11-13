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
import { DesignStats, DesignToolbar, DesignState, DesignBadge } from "./DesignWorkspace";
import { WorkspaceDialog } from "@/components/ui/workspace-dialog";
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
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [actionError, setActionError] = useState("");
  const [selected, setSelected] = useState<Scenario | null>(null);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
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
    setDeleting(true);
    setActionError("");
    try {
      const response = await apiFetch(`/${kind}/${encodeURIComponent(id)}?project_id=${encodeURIComponent(projectId)}`, { method: "DELETE" });
      if (!response.ok) throw new Error(typeof response.data?.detail === "string" ? response.data.detail : "Could not delete record.");
      setDeleteId(null);
      await load();
    } catch (failure) {
      setActionError(failure instanceof Error ? failure.message : "Could not delete record.");
    } finally { setDeleting(false); }
  }

  const count = kind === "scenarios" ? scenarios.length : cases.length;
  const visibleScenarios = scenarios.filter(item => `${item.scenario_id} ${item.title} ${item.story_id}`.toLowerCase().includes(query.toLowerCase()) && (statusFilter === "all" || (statusFilter === "approved" ? item.approved : !item.approved)));
  const visibleCases = cases.filter(item => `${item.testcase_id} ${item.title} ${item.scenario_id}`.toLowerCase().includes(query.toLowerCase()) && (statusFilter === "all" || item.status?.toLowerCase() === statusFilter));
  const caseStatuses = Array.from(new Set(cases.map(item => item.status?.toLowerCase()).filter(Boolean)));
  const visibleCount = kind === "scenarios" ? visibleScenarios.length : visibleCases.length;
  const projectPath = `/projects/${encodeURIComponent(projectId)}`;
  return (
    <div className="design-page catalog-page">
      <div className="workspace-page-header">
        <div><p className="workspace-eyebrow">Test design</p><h1>{title}</h1><p className="workspace-description">{kind === "scenarios" ? "Review what to verify before designing detailed test cases." : "Review procedures, approve explicit expectations and export test designs."}</p></div>
        <Link className="workspace-button" href={`${projectPath}/stories`}>Open stories to create or generate</Link>
      </div>
      {kind === "testcases" && enabled("reusable_workflows") && <VisualSpecificationPanel projectId={projectId} canApprove={canApprove} />}
      <CatalogCreation key={projectId} kind={kind} projectId={projectId} onSaved={async () => { await load(); }} />
      {!loading && !error && <DesignStats items={[{ label: "On this page", value: count }, { label: kind === "scenarios" ? "Approved coverage" : "With expected results", value: kind === "scenarios" ? scenarios.filter(item => item.approved).length : cases.filter(item => item.assertions?.length || item.steps?.some(step => step.expected?.trim())).length }, { label: "Matching records", value: visibleCount }]} />}
      <DesignToolbar query={query} onQuery={setQuery} placeholder={`Search ${title.toLowerCase()} on this page`}>
        <label>Status<select aria-label="Status" value={statusFilter} onChange={event => setStatusFilter(event.target.value)}><option value="all">All statuses</option>
          {kind === "scenarios" ? <><option value="approved">Approved</option><option value="pending">Pending approval</option></> : caseStatuses.map(status => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}
        </select></label>
      </DesignToolbar>
      {actionError && !deleteId && <p role="alert">{actionError}</p>}
      {loading ? <p role="status">Loading {title.toLowerCase()}…</p> : error ? (
        <div role="alert"><p>{error}</p><button className="workspace-button" onClick={() => void load()}>Try again</button></div>
      ) : <>
        {visibleCount === 0 && <DesignState title={count ? "No matching records" : `No ${title.toLowerCase()} on this page`}><p>{count ? "Adjust your search or status filter." : "Add a record or generate from a source above. Scenarios describe coverage; test cases define steps and explicit expected results."}</p></DesignState>}
        {kind === "scenarios" ? visibleScenarios.map(scenario => (
          <article className="catalog-card space-y-3" key={scenario.scenario_id}>
            <div className="design-record-heading"><div><p className="design-record-id">{scenario.scenario_id}</p><h2>{scenario.title}</h2></div><DesignBadge tone={scenario.approved ? "positive" : "warning"}>{scenario.approved ? "Approved" : "Pending approval"}</DesignBadge></div>
            <p>{scenario.purpose || scenario.description || "Coverage intent for the linked story."}</p>
            <div className="catalog-actions">
              <Link href={`${projectPath}/stories/${encodeURIComponent(scenario.story_id)}`}>Story {scenario.story_id}</Link>
              <button className="workspace-button" onClick={() => setSelected(scenario)}>Review scenario</button>
              {scenario.created_by === user?.email && <>
                <button className="workspace-button" onClick={() => setEditingScenario(scenario)}>Edit scenario</button>
                <button className="workspace-button design-danger" disabled={deleting} onClick={() => { setActionError(""); setDeleteId(scenario.scenario_id); }}>Delete scenario</button>
              </>}
            </div>
          </article>
        )) : visibleCases.map(testcase => (
          <article className="catalog-card space-y-3" key={testcase.testcase_id}>
            <div className="design-record-heading"><div><p className="design-record-id">{testcase.testcase_id} · {testcase.complexity || "Unspecified complexity"}</p><h2>{testcase.title}</h2></div><DesignBadge>{testcase.status?.replaceAll("_", " ") || "Unspecified status"}</DesignBadge></div>
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
            <div className="catalog-actions">
              <Link href={`${projectPath}/scenarios`}>Source scenario {testcase.scenario_id}</Link>
              {enabled("test_execution_ui", "test_generation", "approved_visual_run_admission") && <Link href={`${projectPath}/test-execution`}>Review execution setup</Link>}
              {testcase.created_by === user?.email && <>
                <button className="workspace-button" onClick={() => setEditingCase(testcase)}>Edit test case</button>
                <button className="workspace-button design-danger" disabled={deleting} onClick={() => { setActionError(""); setDeleteId(testcase.testcase_id); }}>Delete test case</button>
              </>}
            </div>
          </article>
        ))}
        <nav className="design-pagination" aria-label="Catalog pages">
          <button className="workspace-button" disabled={page === 0} onClick={() => { setPage(page - 1); setQuery(""); setStatusFilter("all"); }}>Previous</button>
          <span>Page {page + 1}</span>
          <button className="workspace-button" disabled={count < 50} onClick={() => { setPage(page + 1); setQuery(""); setStatusFilter("all"); }}>Next</button>
        </nav>
      </>}
      {deleteId && <WorkspaceDialog open title="Delete record" onClose={() => setDeleteId(null)} busy={deleting}>
        <h2 className="text-lg font-semibold">Delete {deleteId}?</h2><p>This cannot be undone. Records with dependent tests, approvals or execution history are protected.</p>
        {actionError && <p role="alert">{actionError}</p>}<div className="catalog-actions"><button className="workspace-button" disabled={deleting} onClick={() => setDeleteId(null)}>Cancel</button><button className="workspace-button design-danger" disabled={deleting} onClick={() => void removeRecord(deleteId)}>{deleting ? "Deleting…" : "Delete record"}</button></div>
      </WorkspaceDialog>}
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
