"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/utils/api";
import { DesignBadge, DesignState, DesignStats, DesignToolbar } from "./DesignWorkspace";

type Execution = { execution_id: string; project_id: string; testcase_id?: string; status?: string; started_at?: string };

/** Read-only legacy history. Never combines lifecycle/status with a new business verdict. */
export default function ExecutionHistory({ projectId }: { projectId: string }) {
  const [rows, setRows] = useState<Execution[]>([]);
  const [page, setPage] = useState(0);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [more, setMore] = useState(false);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    apiFetch(`/execute?skip=${page * 200}&limit=200`, { signal: AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]), cache: "no-store" })
      .then(response => {
        if (controller.signal.aborted) return;
        if (!response.ok || !Array.isArray(response.data)) throw new Error("HISTORY_UNAVAILABLE");
        setRows(response.data.filter((row: Execution) => row.project_id === projectId));
        setMore(response.data.length === 200);
      }).catch(() => { if (!controller.signal.aborted) setError(true); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [projectId, page, revision]);
  const visible = rows.filter(row => `${row.execution_id} ${row.testcase_id || ""}`.toLowerCase().includes(query.toLowerCase()) && (status === "all" || row.status === status));
  const statuses = Array.from(new Set(rows.map(row => row.status).filter((value): value is string => !!value)));
  function reload(nextPage = page) { setLoading(true); setError(false); setRows([]); setPage(nextPage); setRevision(value => value + 1); }
  return <div className="design-page">
    <header className="workspace-page-header"><div><p className="workspace-eyebrow">Execution records</p><h1>Execution history</h1><p className="workspace-description">Inspect recorded outcomes without starting or replaying a run.</p></div>
      <button className="workspace-button" disabled={loading} onClick={() => reload()}>Refresh history</button></header>
    <div className="design-guide"><strong>Historical results stay unchanged</strong><p>Statuses are shown as originally recorded. Development runs remain in their own evidence views. A completed browser action does not by itself mean a business test passed.</p></div>
    {!loading && !error && <DesignStats items={[{ label: "Project records on this page", value: rows.length }, { label: "Matching records", value: visible.length }]} />}
    <DesignToolbar query={query} onQuery={setQuery} placeholder="Search execution or test case ID on this page"><label>Status<select aria-label="Status" value={status} onChange={event => setStatus(event.target.value)}><option value="all">All statuses</option>{statuses.map(value => <option key={value}>{value}</option>)}</select></label></DesignToolbar>
    {loading ? <DesignState title="Loading execution history…" /> : error ? <DesignState error title="Execution history unavailable"><p>Check your connection and try again.</p><button className="workspace-button" onClick={() => reload()}>Try again</button></DesignState> : <>
      {visible.length ? <div className="workspace-table-scroll design-table" role="region" aria-label="Recorded executions" tabIndex={0}><table><thead><tr><th>Execution</th><th>Test case</th><th>Recorded status</th><th>Started</th></tr></thead><tbody>{visible.map(row => <tr key={row.execution_id}>
        <td><code>{row.execution_id}</code></td><td>{row.testcase_id || "Not recorded"}</td><td><DesignBadge>{row.status || "Unknown"}</DesignBadge></td><td>{row.started_at ? new Date(row.started_at).toLocaleString() : "Not recorded"}</td>
      </tr>)}</tbody></table></div> : <DesignState title={rows.length ? "No matching executions" : "No project executions on this page"}><p>{rows.length ? "Adjust the search or status filter." : "Other history pages may contain records for this project. Use Next when available."}</p></DesignState>}
      <nav className="design-pagination" aria-label="History pages"><button className="workspace-button" disabled={page === 0} onClick={() => { setStatus("all"); setQuery(""); reload(page - 1); }}>Previous</button><span>History page {page + 1} · search applies to this page</span><button className="workspace-button" disabled={!more} onClick={() => { setStatus("all"); setQuery(""); reload(page + 1); }}>Next</button></nav>
    </>}
    <Link className="design-back-link" href={`/projects/${encodeURIComponent(projectId)}`}>Back to project overview</Link>
  </div>;
}
