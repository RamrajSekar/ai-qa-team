"use client";

import { useState } from "react";
import { apiFetch } from "@/utils/api";
import type { CatalogCase } from "./ProjectTestCatalog";

export default function TestCaseEditor({ testcase, projectId, onClose, onSaved, create = false }: {
  testcase: CatalogCase; projectId: string; create?: boolean; onClose: () => void; onSaved: () => Promise<void>;
}) {
  const [title, setTitle] = useState(testcase.title);
  const [description, setDescription] = useState(testcase.description || "");
  const [steps, setSteps] = useState(testcase.steps);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function save() {
    setBusy(true);
    setError("");
    try {
      const path = create ? `/testcases/draft?project_id=${encodeURIComponent(projectId)}&scenario_id=${encodeURIComponent(testcase.scenario_id)}`
        : `/testcases/${encodeURIComponent(testcase.testcase_id)}?project_id=${encodeURIComponent(projectId)}`;
      const response = await apiFetch(path, {
        method: create ? "POST" : "PATCH", body: JSON.stringify({ title, description, steps }),
      });
      if (!response.ok) throw new Error(typeof response.data?.detail === "string" ? response.data.detail : "Could not update test case.");
      await onSaved();
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Could not update test case."); }
    finally { setBusy(false); }
  }

  return <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
    <section role="dialog" aria-modal="true" aria-labelledby="edit-test-title" className="bg-white rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 space-y-4">
      <h2 id="edit-test-title" className="text-xl font-semibold">{create ? "Add Test Case" : "Edit Test Case"}</h2>
      <p>Changes require renewed visual-run approval. Earlier approved versions remain in history.</p>
      <label className="block">Title<input className="block w-full border rounded p-2" value={title} onChange={event => setTitle(event.target.value)} /></label>
      <label className="block">Description<textarea className="block w-full border rounded p-2" value={description} onChange={event => setDescription(event.target.value)} /></label>
      {steps.map((step, index) => <div key={index} className="border rounded p-3 space-y-2">
        <label className="block">Step {index + 1}<textarea className="block w-full border rounded p-2" value={step.description || step.action}
          onChange={event => setSteps(rows => rows.map((row, position) => position === index ? { ...row, description: event.target.value } : row))} /></label>
        <label className="block">Expected result {index + 1}<textarea className="block w-full border rounded p-2" value={step.expected || ""}
          onChange={event => setSteps(rows => rows.map((row, position) => position === index ? { ...row, expected: event.target.value } : row))} /></label>
      </div>)}
      <button className="workspace-button" onClick={() => setSteps(rows => [...rows, { action: "unknown", description: "", expected: "" }])}>Add step</button>
      {error && <p role="alert">{error}</p>}
      <div className="flex gap-3"><button className="workspace-button" disabled={busy} onClick={onClose}>Cancel</button>
        <button className="workspace-button" disabled={busy || !title.trim()} onClick={() => void save()}>{busy ? "Saving…" : "Save changes"}</button></div>
    </section>
  </div>;
}
