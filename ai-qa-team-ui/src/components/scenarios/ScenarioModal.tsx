"use client";

import { useState } from "react";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";
import { WorkspaceDialog } from "@/components/ui/workspace-dialog";
import { apiFetch } from "@/utils/api";
import type { Scenario, StepModel } from "@/types/scenario";

interface ScenarioModalProps {
  open: boolean;
  onClose: () => void;
  onSaved: () => Promise<void>;
  storyId: string;
  projectId: string;
  scenario?: Scenario; // Edit mode if exists
}

export default function ScenarioModal({
  open,
  onClose,
  onSaved,
  storyId,
  projectId,
  scenario,
}: ScenarioModalProps) {
  const { enabled } = useFeatures();
  const intentMode = scenario ? scenario.spec_kind === "coverage-intent-v1" : enabled("product_knowledge");
  const [purpose, setPurpose] = useState(scenario?.purpose || "");
  const [expected, setExpected] = useState(scenario?.expected_outcome || "");
  const [role, setRole] = useState(scenario?.role || "");
  const [coverage, setCoverage] = useState(scenario?.coverage_type || "happy_path");
  const [preconditions, setPreconditions] = useState((scenario?.preconditions || []).join("\n"));
  const isEdit = !!scenario;

  const [title, setTitle] = useState(scenario?.title ?? "");
  const [description, setDescription] = useState(scenario?.description ?? "");
  const [steps, setSteps] = useState<StepModel[]>(scenario?.steps ?? []);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  if (!open) return null;

  /** Save or Update */
  async function handleSave() {
    if (!title.trim()) return;

    setSaving(true);
    setError("");

    const payload = {
      story_id: storyId,
      title,
      description,
      ...(intentMode ? { purpose: purpose || title, expected_outcome: expected, role: role || null, coverage_type: coverage, preconditions: preconditions.split("\n").filter(Boolean), ...(scenario ? { acceptance_criteria_refs: scenario.acceptance_criteria_refs, rule_references: scenario.rule_references } : {}) } : {}),
      steps: intentMode ? [] : steps.map(step => ({ ...step, action: step.action.trim(), expected: step.expected?.trim() || null })),
    };

    const url = isEdit
      ? `/scenarios/${scenario?.scenario_id}?project_id=${projectId}`
      : "/scenarios";

    const method = isEdit ? "PATCH" : "POST";

    try {
      const res = await apiFetch(url, { method, body: JSON.stringify(payload) });
      if (!res.ok) throw new Error(typeof res.data?.detail === "string" ? res.data.detail : "Could not save scenario.");
      await onSaved();
      onClose();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not save scenario.");
    } finally {
      setSaving(false);
    }
  }

  const canSave = title.trim() && (intentMode ? expected.trim() : steps.every(step => step.action.trim()));

  return (
    <WorkspaceDialog open={open} onClose={onClose} title={isEdit ? "Edit Scenario" : "Create Scenario"} busy={saving} className="workspace-dialog-wide">

        <h2 className="text-xl font-semibold mb-4">
          {isEdit ? "Edit Scenario" : "Create Scenario"}
        </h2>

        <div className="space-y-4">
          
          {/* Title */}
          <div>
            <label htmlFor="scenario-title" className="font-medium text-sm">Title</label>
            <input
              id="scenario-title"
              className="w-full border p-2 rounded mt-1"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="User logs in and sees dashboard"
            />
          </div>

          {/* Description */}
          <div>
            <label htmlFor="scenario-description" className="font-medium text-sm">Description</label>
            <textarea
              id="scenario-description"
              className="w-full border p-2 rounded mt-1"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          {intentMode ? <fieldset disabled={saving} className="space-y-2"><legend>Coverage intent — what to verify</legend>
            <label className="block">Purpose<input className="border rounded w-full" value={purpose} onChange={event => setPurpose(event.target.value)} /></label>
            <label className="block">Application role<input className="border rounded w-full" value={role} onChange={event => setRole(event.target.value)} /></label>
            <label className="block">Coverage<select value={coverage} onChange={event => setCoverage(event.target.value as typeof coverage)}>{["happy_path", "negative", "boundary", "exception"].map(value => <option key={value}>{value}</option>)}</select></label>
            <label className="block">Preconditions (one per line)<textarea className="border rounded w-full" value={preconditions} onChange={event => setPreconditions(event.target.value)} /></label>
            <label className="block">Explicit expected outcome<textarea className="border rounded w-full" value={expected} onChange={event => setExpected(event.target.value)} /></label>
            <p>Detailed actions belong in test cases. The server links new intent to the current reviewed story and approved knowledge.</p>
          </fieldset> : <fieldset disabled={saving} className="space-y-2">
            <legend className="font-medium text-sm">Scenario steps</legend>
            {steps.map((step, index) => (
              <div className="space-y-1 border rounded p-2" key={step.step_id}>
                <label className="block">Action {index + 1}
                  <input className="w-full" value={step.action} onChange={event => setSteps(items =>
                    items.map(item => item.step_id === step.step_id ? { ...item, action: event.target.value } : item))} />
                </label>
                <label className="block">Expected result {index + 1}
                  <input className="w-full" value={step.expected ?? ""} onChange={event => setSteps(items =>
                    items.map(item => item.step_id === step.step_id ? { ...item, expected: event.target.value } : item))} />
                </label>
                <button type="button" className="workspace-button"
                  onClick={() => setSteps(items => items.filter(item => item.step_id !== step.step_id))}>Remove step</button>
              </div>
            ))}
            <button type="button" className="workspace-button" onClick={() => {
              const stepId = crypto.randomUUID();
              setSteps(items => [...items, { step_id: stepId, category: "UI", action: "", expected: "" }]);
            }}>Add step</button>
          </fieldset>}
          {error && <p role="alert" className="text-red-700 text-sm">{error}</p>}
        </div>

        <div className="flex justify-end mt-6 gap-3">
          <button onClick={onClose} className="px-4 py-2 border rounded">
            Cancel
          </button>

          <button
            onClick={handleSave}
            disabled={saving || !canSave}
            className={`px-4 py-2 rounded text-white ${
              saving || !canSave
                ? "bg-gray-400 cursor-not-allowed"
                : "bg-purple-600 hover:bg-purple-700"
            }`}
          >
            {saving ? "Saving..." : "Save Scenario"}
          </button>
        </div>
    </WorkspaceDialog>
  );
}
