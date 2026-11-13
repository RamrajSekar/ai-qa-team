"use client";

import { useState } from "react";
import { apiFetch } from "@/utils/api";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";
import ScenarioModal from "@/components/scenarios/ScenarioModal";
import TestCaseEditor from "./TestCaseEditor";

interface Source { id: string; title: string }

export default function CatalogCreation({ kind, projectId, onSaved }: {
  kind: "scenarios" | "testcases"; projectId: string; onSaved: () => Promise<void>;
}) {
  const { enabled } = useFeatures();
  const [count, setCount] = useState(kind === "scenarios" ? 3 : 1);
  const [open, setOpen] = useState(false);
  const [sources, setSources] = useState<Source[]>([]);
  const [source, setSource] = useState("");
  const [sourcePage, setSourcePage] = useState(0);
  const [more, setMore] = useState(false);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function loadSources(page = 0) {
    setOpen(true);
    setBusy(true);
    setError("");
    setSources([]);
    setSource("");
    try {
      const path = kind === "scenarios" ? `/stories?project_id=${encodeURIComponent(projectId)}`
        : `/scenarios/project-list?project_id=${encodeURIComponent(projectId)}&skip=${page * 100}&limit=100`;
      const response = await apiFetch(path);
      if (!response.ok || !Array.isArray(response.data)) throw new Error("Could not load source records.");
      const rows: { story_id: string; scenario_id: string; title: string; approved?: boolean }[] = response.data;
      setSources(rows.filter(row => kind === "scenarios" || row.approved).map(row => ({
        id: kind === "scenarios" ? row.story_id : row.scenario_id, title: row.title,
      })));
      setMore(kind === "testcases" && rows.length === 100);
      setSourcePage(page);
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Could not load source records."); }
    finally { setBusy(false); }
  }

  async function generate() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const path = kind === "scenarios"
        ? `/scenarios/generate-from-story?story_id=${encodeURIComponent(source)}&count=${count}&complexity=basic`
        : `/testcases/generate?scenario_id=${encodeURIComponent(source)}&project_id=${encodeURIComponent(projectId)}&count=${count}&complexity=basic`;
      const response = await apiFetch(path, { method: "POST" });
      if (!response.ok) throw new Error(typeof response.data?.detail === "string" ? response.data.detail : response.data?.detail?.message || "Generation could not be completed.");
      if (kind === "scenarios" && !response.data?.scenarios?.length) throw new Error("No scenarios were generated. Check the story’s acceptance criteria.");
      setMessage(kind === "scenarios" ? response.data.summary?.message || `${response.data.scenarios.length} scenarios generated.` : `${Array.isArray(response.data) ? response.data.length : 0} detailed test cases generated. Review before approval.`);
      await onSaved();
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Generation could not be completed."); }
    finally { setBusy(false); }
  }

  return <div className="design-create space-y-3">
    <button className="workspace-button workspace-primary" aria-expanded={open} disabled={busy} onClick={() => void loadSources()}>Add or generate {kind === "scenarios" ? "scenario" : "test case"}</button>
    {open && <div className="design-create-body space-y-3">
      <label className="block">{kind === "scenarios" ? "Source story" : "Approved source scenario"}
        <select className="border rounded p-2 ml-3" value={source} disabled={busy} onChange={event => setSource(event.target.value)}>
          <option value="">Select a source</option>
          {sources.map(row => <option key={row.id} value={row.id}>{row.id} — {row.title}</option>)}
        </select>
      </label>
      {!busy && sources.length === 0 && <p>No eligible sources on this page. Add a story or approve a scenario first.</p>}
      <label className="block">Requested count <input type="number" min={1} max={20} value={count} onChange={event => setCount(Math.max(1, Math.min(20, Number(event.target.value) || 1)))} /></label>
      <div className="catalog-actions">
        <button className="workspace-button" disabled={busy || !source} onClick={() => setEditing(true)}>Add manually</button>
        <button className="workspace-button workspace-primary" disabled={busy || !source || (kind === "scenarios" && !enabled("story_management"))} onClick={() => void generate()}>
          {busy ? "Working…" : kind === "scenarios" ? "Generate with AI" : "Generate test case"}
        </button>
        <button className="workspace-button" disabled={busy} onClick={() => setOpen(false)}>Close</button>
      </div>
      {kind === "testcases" && <p className="text-sm">Scenarios define coverage intent. Knowledge-aware generation produces detailed procedures, data and explicit assertions from an approved scenario. Existing legacy scenarios retain their conversion path.</p>}
      {kind === "testcases" && <div className="catalog-actions">
        <button disabled={busy || sourcePage === 0} onClick={() => void loadSources(sourcePage - 1)}>Previous sources</button>
        <button disabled={busy || !more} onClick={() => void loadSources(sourcePage + 1)}>Next sources</button>
      </div>}
    </div>}
    {error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    {editing && kind === "scenarios" && <ScenarioModal open storyId={source} projectId={projectId}
      onClose={() => setEditing(false)} onSaved={onSaved} />}
    {editing && kind === "testcases" && <TestCaseEditor create projectId={projectId}
      testcase={{ testcase_id: "", scenario_id: source, title: "", status: "draft", steps: [] }}
      onClose={() => setEditing(false)} onSaved={async () => { setEditing(false); await onSaved(); }} />}
  </div>;
}
