"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { apiFetch } from "@/utils/api";
import type { Scenario } from "@/types/scenario";
import { useProjects } from "@/hooks/useProjects";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";
import CreateManualExecution from "./CreateManualExecution";
import { useAuth } from "@/components/providers/AuthProvider";
import ScenarioModal from "@/components/scenarios/ScenarioModal";
import TestCaseEditor from "@/components/projects/TestCaseEditor";
import CatalogCreation from "./CatalogCreation";
import ScenarioViewer from "@/components/scenarios/ScenarioViewer";
import { DesignStats, DesignToolbar, DesignState, DesignBadge, designStatusLabel } from "./DesignWorkspace";
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

type ResultSummary = { design_status?: string | null; approved_version_id: string | null; manual: { verdict: string; recorded_at: string; execution_id?: string | null; version_id?: string } | null; automated: { verdict: string; recorded_at: string; execution_id?: string | null; version_id?: string } | null };

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
  const [selectedCases, setSelectedCases] = useState<{ testcase_id: string; version_id: string; title: string }[]>([]);
  const [creatingExecution, setCreatingExecution] = useState(false);
  const [reviewCase, setReviewCase] = useState<CatalogCase | null>(null);
  const [summaries, setSummaries] = useState<Record<string, ResultSummary> | null>(null);
  const [summaryError, setSummaryError] = useState("");
  const manualEnabled = kind === "testcases" && enabled("manual_test_results");
  const automationEnabled = enabled("automation_execution_ui");
  const loadSummaries = useCallback(async (rows: CatalogCase[], signal?: AbortSignal) => {
    if (!manualEnabled || !rows.length) return;
    setSummaryError("");
    try {
      const ids = rows.map(row => row.testcase_id).join(",");
      const response = await apiFetch(`/projects/${encodeURIComponent(projectId)}/test-results?case_ids=${encodeURIComponent(ids)}`, { signal, cache: "no-store" });
      if (!response.ok || !response.data || Array.isArray(response.data)) throw new Error("Results unavailable. Test specifications remain available.");
      if (!signal?.aborted) setSummaries(response.data);
    } catch { if (!signal?.aborted) { setSummaries(null); setSummaryError("Results unavailable. Test specifications remain available."); } }
  }, [manualEnabled, projectId]);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const title = kind === "scenarios" ? "Scenarios" : "Test Cases";

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    setSummaries(null);
    try {
      const response = await apiFetch(`/${kind}/project-list?project_id=${encodeURIComponent(projectId)}&skip=${page * 50}&limit=50`, { signal });
      if (!response.ok || !Array.isArray(response.data)) {
        throw new Error(`Could not load ${kind === "scenarios" ? "scenarios" : "test cases"} (HTTP ${response.status}).`);
      }
      if (signal?.aborted) return;
      if (kind === "scenarios") setScenarios(response.data);
      // Render specifications as soon as they arrive. Result/approval metadata
      // has its own unavailable state and must not hold the entire table open.
      else { setCases(response.data); void loadSummaries(response.data, signal); }
    } catch (failure) {
      if (!signal?.aborted) setError(failure instanceof Error ? failure.message : "Could not load records.");
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [kind, page, projectId, loadSummaries]);

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
  const designStatus = (item: CatalogCase) => {
    const summary = summaries?.[item.testcase_id];
    if (manualEnabled) return summary ? summary.design_status || (summary.approved_version_id ? "approved" : "draft") : (summaryError ? "unavailable" : "loading");
    return item.status?.toLowerCase() || "draft";
  };
  const visibleCases = cases.filter(item => `${item.testcase_id} ${item.title} ${item.scenario_id}`.toLowerCase().includes(query.toLowerCase()) && (statusFilter === "all" || designStatus(item) === statusFilter));
  const caseStatuses = Array.from(new Set(cases.map(item => designStatus(item)).filter(Boolean)));
  const visibleCount = kind === "scenarios" ? visibleScenarios.length : visibleCases.length;
  const projectPath = `/projects/${encodeURIComponent(projectId)}`;
  return (
    <div className="design-page catalog-page">
      <div className="workspace-page-header">
        <div><p className="workspace-eyebrow">Test design</p><h1>{title}</h1><p className="workspace-description">{kind === "scenarios" ? "Review what to verify before designing detailed test cases." : "Review procedures, approve explicit expectations and export test designs."}</p></div>
        <Link className="workspace-button" href={`${projectPath}/stories`}>Open stories to create or generate</Link>
      </div>
      <CatalogCreation key={projectId} kind={kind} projectId={projectId} onSaved={async () => { await load(); }} />
      {!loading && !error && <DesignStats items={[{ label: "On this page", value: count }, { label: kind === "scenarios" ? "Approved coverage" : "With expected results", value: kind === "scenarios" ? scenarios.filter(item => item.approved).length : cases.filter(item => item.assertions?.length || item.steps?.some(step => step.expected?.trim())).length }, { label: "Matching records", value: visibleCount }]} />}
      <DesignToolbar query={query} onQuery={setQuery} placeholder={`Search ${title.toLowerCase()} on this page`}>
        <label>Status<select aria-label="Status" value={statusFilter} onChange={event => setStatusFilter(event.target.value)}><option value="all">All statuses</option>
          {kind === "scenarios" ? <><option value="approved">Approved</option><option value="pending">In Review</option></> : caseStatuses.map(status => <option key={status} value={status}>{designStatusLabel(status)}</option>)}
        </select></label>
      </DesignToolbar>
      {manualEnabled && <div className="design-selection-bar"><span>{selectedCases.length}/10 approved cases selected</span><button className="workspace-button workspace-primary" disabled={!selectedCases.length} onClick={() => setCreatingExecution(true)}>Create Test Execution</button><Link className="design-back-link" href={`${projectPath}/test-execution`}>View manual executions</Link></div>}
      {summaryError && <div role="alert"><p>{summaryError}</p><button className="workspace-button" onClick={() => void loadSummaries(cases)}>Refresh result summaries</button></div>}
      {actionError && !deleteId && <p role="alert">{actionError}</p>}
      {loading ? <p role="status">Loading {title.toLowerCase()}…</p> : error ? (
        <div role="alert"><p>{error}</p><button className="workspace-button" onClick={() => void load()}>Try again</button></div>
      ) : <>
        {visibleCount === 0 && <DesignState title={count ? "No matching records" : `No ${title.toLowerCase()} on this page`}><p>{count ? "Adjust your search or status filter." : "Add a record or generate from a source above. Scenarios describe coverage; test cases define steps and explicit expected results."}</p></DesignState>}
        {visibleCount > 0 && <div className="workspace-table-scroll design-table" role="region" aria-label={`${title} table; scroll for all columns`} tabIndex={0}>
          <table><thead><tr>{manualEnabled && <th>Select</th>}<th>{kind === "scenarios" ? "Scenario" : "Test case"}</th><th>Source</th><th>{kind === "scenarios" ? "Approval" : "Design status"}</th>
            {manualEnabled && <th>Latest manual result</th>}{kind === "testcases" && automationEnabled && <th>Latest automated result</th>}<th>Actions</th></tr></thead>
          <tbody>{kind === "scenarios" ? visibleScenarios.map(scenario => <tr key={scenario.scenario_id}>
            <td><span className="design-record-id">{scenario.scenario_id}</span><button className="design-title-link" onClick={() => setSelected(scenario)}>{scenario.title}</button><p className="design-excerpt">{scenario.purpose || scenario.description || "Coverage intent"}</p></td>
            <td><Link className="design-back-link" href={`${projectPath}/stories/${encodeURIComponent(scenario.story_id)}`}>Story {scenario.story_id}</Link></td>
            <td><DesignBadge tone={scenario.approved ? "positive" : "warning"}>{scenario.approved ? "Approved" : "In Review"}</DesignBadge></td>
            <td><div className="design-row-actions"><button className="workspace-button" onClick={() => setSelected(scenario)} aria-label="Review scenario">Review</button>{scenario.created_by === user?.email && <><button className="workspace-button" onClick={() => setEditingScenario(scenario)} aria-label="Edit scenario">Edit</button><button className="workspace-button design-danger" disabled={deleting} onClick={() => { setActionError(""); setDeleteId(scenario.scenario_id); }} aria-label="Delete scenario">Delete</button></>}</div></td>
          </tr>) : visibleCases.map(testcase => <tr key={testcase.testcase_id}>
            {manualEnabled && <td><input type="checkbox" aria-label={`Select ${testcase.testcase_id}`} checked={selectedCases.some(item => item.testcase_id === testcase.testcase_id)} disabled={!summaries?.[testcase.testcase_id]?.approved_version_id || (selectedCases.length >= 10 && !selectedCases.some(item => item.testcase_id === testcase.testcase_id))} onChange={event => { const version = summaries?.[testcase.testcase_id]?.approved_version_id; if (version) setSelectedCases(rows => event.target.checked ? [...rows, { testcase_id: testcase.testcase_id, version_id: version, title: testcase.title }] : rows.filter(item => item.testcase_id !== testcase.testcase_id)); }} /></td>}
            <td><span className="design-record-id">{testcase.testcase_id} · {testcase.complexity || "Unspecified complexity"}</span><button className="design-title-link" onClick={() => setReviewCase(testcase)}>{testcase.title}</button>{testcase.description && <p className="design-excerpt">{testcase.description}</p>}</td>
            <td><Link className="design-back-link" href={`${projectPath}/scenarios`}>Scenario {testcase.scenario_id}</Link></td>
            <td><DesignBadge>{designStatusLabel(designStatus(testcase))}</DesignBadge></td>
            {manualEnabled && <td>{summaries ? <DesignBadge>{summaries[testcase.testcase_id]?.manual?.verdict.replaceAll("_", " ") || "Not run"}</DesignBadge> : (summaryError ? "Unavailable" : "Loading…")}{summaries?.[testcase.testcase_id]?.manual?.execution_id && <Link className="design-result-link" title={summaries[testcase.testcase_id].manual!.execution_id!} aria-label={`Open test execution ${summaries[testcase.testcase_id].manual!.execution_id}`} href={`${projectPath}/test-execution?execution=${encodeURIComponent(summaries[testcase.testcase_id].manual!.execution_id!)}`}>Execution {summaries[testcase.testcase_id].manual!.execution_id!.slice(0, 8)}</Link>}</td>}
            {automationEnabled && <td>{summaries?.[testcase.testcase_id]?.automated?.verdict.replaceAll("_", " ") || "Not recorded in this result system"}</td>}
            <td><div className="design-row-actions"><button className="workspace-button" onClick={() => setReviewCase(testcase)} aria-label="Review test case">Review</button>
              {testcase.created_by === user?.email && <><button className="workspace-button" onClick={() => setEditingCase(testcase)} aria-label="Edit test case">Edit</button><button className="workspace-button design-danger" disabled={deleting} onClick={() => { setActionError(""); setDeleteId(testcase.testcase_id); }} aria-label="Delete test case">Delete</button></>}
            </div></td>
          </tr>)}</tbody></table>
        </div>}
        <nav className="design-pagination" aria-label="Catalog pages">
          <button className="workspace-button" disabled={page === 0} onClick={() => { setPage(page - 1); setSelectedCases([]); setQuery(""); setStatusFilter("all"); }}>Previous</button>
          <span>Page {page + 1}</span>
          <button className="workspace-button" disabled={count < 50} onClick={() => { setPage(page + 1); setSelectedCases([]); setQuery(""); setStatusFilter("all"); }}>Next</button>
        </nav>
      </>}
      {creatingExecution && <CreateManualExecution projectId={projectId} cases={selectedCases} onClose={() => setCreatingExecution(false)} />}
      {reviewCase && <WorkspaceDialog open title={`Review test case: ${reviewCase.title}`} onClose={() => { setReviewCase(null); void loadSummaries(cases); }} className="workspace-dialog-wide">
        <div className="design-page"><header><p className="workspace-eyebrow">{reviewCase.testcase_id} · Test design</p><h2 className="text-xl font-semibold">{reviewCase.title}</h2><p>{reviewCase.description || reviewCase.purpose}</p></header>
          <details open><summary>Steps and expected results</summary><ol className="list-decimal pl-6 space-y-2">{reviewCase.steps.map((step, i) => <li key={i}><p>{step.description || step.action}</p><p>Expected result — {step.expected || "No explicit expected result recorded"}</p></li>)}</ol></details>
          {reviewCase.knowledge_version_id && <details><summary>Purpose, data and approved context</summary><p>Purpose: {reviewCase.purpose}</p><p>Role: {reviewCase.role || "Not specified"}</p><p>Preconditions: {reviewCase.preconditions?.join("; ")}</p><p>Public data: {Object.entries(reviewCase.public_data || {}).map(([key, value]) => `${key}: ${value}`).join("; ")}</p><p>Assertions: {reviewCase.assertions?.join("; ")}</p><p>Cleanup: {reviewCase.cleanup?.join("; ") || "None specified"}</p><p>Acceptance criteria: {reviewCase.acceptance_criteria_refs?.join("; ")}</p><p>Rules: {reviewCase.rule_references?.join(", ")}</p><p>Knowledge version: {reviewCase.knowledge_version_id}</p></details>}
          {(manualEnabled || enabled("product_knowledge", "story_analysis")) && <TestDesignReview key={`${reviewCase.testcase_id}:${reviewCase.updated_at || ""}`} testcase={reviewCase} projectId={projectId} canApprove={canApprove} />}
        </div>
      </WorkspaceDialog>}
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
