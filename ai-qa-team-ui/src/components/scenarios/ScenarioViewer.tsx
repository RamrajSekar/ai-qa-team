"use client";

import { X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import type { Scenario } from "@/types/scenario";
import { apiFetch } from "@/utils/api";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";

interface Props {
  open: boolean;
  scenario: Scenario | null;
  onClose: () => void;
  onApproved: (scenario: Scenario) => void;
}

export default function ScenarioViewer({ open, scenario, onClose, onApproved }: Props) {
  const { enabled } = useFeatures();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [generatedIds, setGeneratedIds] = useState<string[]>([]);
  if (!open || !scenario) return null;

  async function perform(path: string, method: "POST" | "PUT", onSuccess: (data: unknown) => void) {
    setBusy(true);
    setError("");
    try {
      const response = await apiFetch(path, { method });
      if (!response.ok) {
        throw new Error(typeof response.data?.detail === "string" ? response.data.detail : "The request was rejected.");
      }
      onSuccess(response.data);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not complete the request.");
    } finally {
      setBusy(false);
    }
  }

  const scenarioId = encodeURIComponent(scenario.scenario_id);
  const projectId = encodeURIComponent(scenario.project_id);
  const canGenerate = enabled("test_generation") && scenario.approved && scenario.steps.length > 0;
  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
      <div className="bg-white rounded-lg w-full max-w-3xl p-6 shadow-xl relative">
        
        <button
          onClick={onClose}
          aria-label="Close scenario"
          className="absolute right-4 top-4 text-gray-500 hover:text-black"
        >
          <X size={20} />
        </button>

        <h2 className="text-xl font-semibold mb-4">Scenario Details</h2>

        <div className="space-y-3">
          <div>
            <p className="text-xs text-gray-500">Scenario ID</p>
            <p className="font-medium">{scenario.scenario_id}</p>
          </div>

          <div>
            <p className="text-xs text-gray-500">Title</p>
            <p className="font-medium">{scenario.title}</p>
          </div>

          {scenario.description && (
            <div>
              <p className="text-xs text-gray-500">Description</p>
              <p>{scenario.description}</p>
            </div>
          )}

          <div>
            <p className="text-xs text-gray-500">Status</p>
            <p>{scenario.approved ? "Approved" : "Pending approval"}</p>
          </div>

          <div>
            <p className="text-xs text-gray-500 mb-1">Steps</p>

            {scenario.steps.length === 0 ? (
              <p className="text-gray-500 italic">No steps defined.</p>
            ) : (
              <div className="border rounded p-3 bg-gray-50 max-h-72 overflow-auto">
                {scenario.steps.map((step, idx) => (
                  <div key={idx} className="p-2 border-b last:border-b-0">
                    <p className="font-medium text-sm">
                      Step {idx + 1}: {step.action}
                    </p>
                    {step.expected && (
                      <p className="text-xs text-gray-600">
                        Expected: {step.expected}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {error && <p role="alert" className="mt-4 text-sm text-red-700">{error}</p>}
        {generatedIds.length > 0 && <p role="status" className="mt-4 text-sm">
          Generated {generatedIds.join(", ")}.{" "}
          <Link className="underline" href={`/projects/${projectId}#approved-visual-run`}>Open Project Overview</Link>
        </p>}
        <div className="flex flex-wrap justify-end gap-2 mt-6">
          {!scenario.approved && <button type="button" className="workspace-button" disabled={busy || !scenario.steps.length}
            onClick={() => void perform(`/scenarios/${scenarioId}/approve`, "PUT", data => onApproved(data as Scenario))}>
            Approve scenario
          </button>}
          {canGenerate && <button type="button" className="workspace-button workspace-primary" disabled={busy || generatedIds.length > 0}
            onClick={() => void perform(`/testcases/generate?scenario_id=${scenarioId}&project_id=${projectId}&count=1&complexity=basic`, "POST", data => {
              if (!Array.isArray(data) || !data.length) throw new Error("No test cases were returned.");
              setGeneratedIds(data.map(item => item.testcase_id));
            })}>Generate test case</button>}
          <button
            onClick={onClose}
            className="px-4 py-2 border rounded hover:bg-gray-100"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
