"use client";

import { X } from "lucide-react";
import type { Scenario } from "@/types/scenario";

interface Props {
  open: boolean;
  scenario: Scenario | null;
  onClose: () => void;
}

export default function ScenarioViewer({ open, scenario, onClose }: Props) {
  if (!open || !scenario) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
      <div className="bg-white rounded-lg w-full max-w-3xl p-6 shadow-xl relative">
        
        <button
          onClick={onClose}
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
            <p className="capitalize">{scenario.status}</p>
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

        <div className="text-right mt-6">
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
