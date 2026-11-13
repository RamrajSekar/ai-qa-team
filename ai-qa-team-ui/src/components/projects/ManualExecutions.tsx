"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/utils/api";
import { DesignBadge, DesignState } from "./DesignWorkspace";
import ManualResultPanel from "./ManualResultPanel";

interface Entry { execution_id: string; title: string; release_cycle: string; case_count: number; created_at: string }
interface Case { testcase_id: string; specification: { approved_by?: string; approved_by_display_name?: string; approved_at?: string; version_id: string; case: { title: string } } }
interface Execution { execution_id: string; lifecycle: string; completed_count: number; manifest: { title: string; release_cycle: string; mode: string; cases: Case[] }; results: { testcase_id: string; verdict: string; actual_result: string; executor_display_name?: string | null }[] }

export default function ManualExecutions({ projectId, executionId }: { projectId: string; executionId: string | null }) {
  const [entries, setEntries] = useState<Entry[]>([]); const [execution, setExecution] = useState<Execution | null>(null);
  const [selected, setSelected] = useState<Case | null>(null); const [skip, setSkip] = useState(0); const [more, setMore] = useState(false);
  const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  const root = `/projects/${encodeURIComponent(projectId)}`;
  const load = useCallback(async (signal?: AbortSignal) => {
    const response = await apiFetch(`/projects/${encodeURIComponent(projectId)}/test-results/executions${executionId ? `/${encodeURIComponent(executionId)}` : `?skip=${skip}`}`, { signal, cache: "no-store" });
    if (!response.ok) throw new Error("Could not load manual test executions.");
    if (!signal?.aborted) { if (executionId) setExecution(response.data); else { setEntries(response.data.records); setMore(response.data.has_more); } }
  }, [projectId, executionId, skip]);
  useEffect(() => {
    const controller = new AbortController();
    async function fetchExecution() {
      try { await load(controller.signal); }
      catch { if (!controller.signal.aborted) setError("Could not load manual test executions."); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    }
    void fetchExecution();
    return () => controller.abort();
  }, [load]);
  return <div className="design-page"><header className="workspace-page-header"><div><p className="workspace-eyebrow">Manual testing</p><h1>Test Execution</h1><p className="workspace-description">Group approved test cases by release or cycle, then record each case’s result.</p></div><Link className="workspace-button workspace-primary" href={`${root}/testcases`}>Select approved test cases</Link></header>
    {error && <DesignState error title={error}><button className="workspace-button" onClick={() => { setError(""); void load().catch(() => setError("Could not reload executions.")); }}>Try again</button></DesignState>}
    {loading ? <DesignState title="Loading manual executions…" /> : execution ? <>
      <section><div className="design-record-heading"><h2 className="text-xl font-semibold">{execution.manifest.title}</h2><DesignBadge>{execution.lifecycle.replaceAll("_", " ")}</DesignBadge></div><p className="whitespace-pre-wrap">Release / Cycle: {execution.manifest.release_cycle}</p><p>Mode: Manual · {execution.completed_count}/{execution.manifest.cases.length} case results recorded</p><p className="workspace-metadata">Completion means results were recorded; it does not mean every case passed.</p></section>
      <div className="workspace-table-scroll design-table" role="region" aria-label="Execution cases" tabIndex={0}><table><thead><tr><th>Test case</th><th>Actual result</th><th>Result</th><th>Executed By</th><th>Actions</th></tr></thead><tbody>{execution.manifest.cases.map(item => { const result = execution.results.find(row => row.testcase_id === item.testcase_id); return <tr key={item.testcase_id}><td>{item.specification.case.title}{item.specification.approved_by && <p className="workspace-metadata">Approved by {item.specification.approved_by_display_name || "Project member"}{item.specification.approved_at ? ` · ${new Date(item.specification.approved_at).toLocaleString()}` : ""}</p>}</td><td><span className="design-excerpt">{result?.actual_result || "Not recorded"}</span></td><td><DesignBadge>{result?.verdict.replaceAll("_", " ") || "Not run"}</DesignBadge></td><td>{result ? result.executor_display_name || "Name not recorded" : "Not executed"}</td><td><button className="workspace-button" onClick={() => setSelected(item)}>{result ? "View result" : "Record result"}</button></td></tr>; })}</tbody></table></div>
      <Link className="design-back-link" href={`${root}/test-execution`}>All manual executions</Link>
    </> : !error && <>
      {!entries.length ? <DesignState title="No manual executions on this page"><p>Select approved Test Cases and enter Release/Cycle details to create one.</p></DesignState> : <div className="workspace-table-scroll design-table" role="region" aria-label="Manual test executions" tabIndex={0}><table><thead><tr><th>Execution</th><th>Release / Cycle</th><th>Cases</th><th>Mode</th><th>Created</th></tr></thead><tbody>{entries.map(item => <tr key={item.execution_id}><td><Link className="design-back-link" href={`${root}/test-execution?execution=${item.execution_id}`}>{item.title}</Link></td><td><span className="design-excerpt">{item.release_cycle}</span></td><td>{item.case_count}</td><td>Manual</td><td>{new Date(item.created_at).toLocaleString()}</td></tr>)}</tbody></table></div>}
      <nav className="design-pagination" aria-label="Manual execution pages"><button className="workspace-button" disabled={skip === 0} onClick={() => { setLoading(true); setSkip(skip - 20); }}>Previous</button><span>Page {skip / 20 + 1}</span><button className="workspace-button" disabled={!more} onClick={() => { setLoading(true); setSkip(skip + 20); }}>Next</button></nav>
    </>}
    {selected && execution && <ManualResultPanel key={selected.testcase_id} projectId={projectId} testcaseId={selected.testcase_id} title={selected.specification.case.title} executionId={execution.execution_id} onClose={() => setSelected(null)} onSaved={load} />}
  </div>;
}
