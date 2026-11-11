"use client";

import { X, ListTree, FileJson } from "lucide-react";
import { useState } from "react";
import type { Recording } from "@/types/recorder";

interface Props {
  open: boolean;
  onClose: () => void;
  recording: Recording | null;
}

export default function RecordingViewer({ open, onClose, recording }: Props) {
  const [tab, setTab] = useState<"steps" | "json">("steps");

  if (!open || !recording) return null;

  return (
    <div className="fixed inset-0 z-[9999] bg-black/60 flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-3xl rounded-lg shadow-xl overflow-hidden">
        {/* HEADER */}
        <div className="flex items-center justify-between px-5 py-3 border-b bg-gray-50">
          <h2 className="text-lg font-semibold">
            Recording – {recording.recording_id}
          </h2>

          <button
            className="text-gray-600 hover:text-red-500"
            onClick={onClose}
          >
            <X size={24} />
          </button>
        </div>

        {/* METADATA */}
        <div className="px-5 py-3 text-sm text-gray-600 border-b bg-gray-50/50">
          <p>
            <strong>Story:</strong> {recording.story_id}
          </p>
          <p>
            <strong>Created:</strong>{" "}
            {new Date(recording.created_at).toLocaleString()}
          </p>
          <p>
            <strong>Steps:</strong> {recording.steps?.length ?? 0}
          </p>
        </div>

        {/* TABS */}
        <div className="flex border-b bg-gray-100 text-sm">
          <button
            onClick={() => setTab("steps")}
            className={`flex items-center gap-1 px-4 py-2 hover:bg-gray-200 ${
              tab === "steps" ? "font-semibold border-b-2 border-indigo-600" : ""
            }`}
          >
            <ListTree size={16} /> Steps
          </button>

          <button
            onClick={() => setTab("json")}
            className={`flex items-center gap-1 px-4 py-2 hover:bg-gray-200 ${
              tab === "json" ? "font-semibold border-b-2 border-indigo-600" : ""
            }`}
          >
            <FileJson size={16} /> JSON
          </button>
        </div>

        {/* CONTENT */}
        <div className="p-5 max-h-[400px] overflow-y-auto">
          {tab === "steps" ? (
            <StepsList recording={recording} />
          ) : (
            <JsonView recording={recording} />
          )}
        </div>

        {/* FOOTER FUTURE ACTIONS */}
        <div className="p-4 border-t bg-gray-50 flex justify-between text-sm text-gray-500">
          <div>Extend: Replay, Export, Compare…</div>

          <button
            onClick={onClose}
            className="px-4 py-1 bg-gray-900 text-white rounded hover:bg-gray-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

/* -------------------------------------------------------
    STEPS LIST COMPONENT
------------------------------------------------------- */
function StepsList({ recording }: { recording: Recording }) {
  if (!recording.steps?.length) {
    return <p className="text-gray-500">No steps recorded.</p>;
  }

  return (
    <div className="space-y-3">
      {recording.steps.map((step: any, index: number) => (
        <div
          key={index}
          className="border rounded p-3 bg-white shadow-sm"
        >
          <p className="text-sm text-gray-700">
            <strong>#{index + 1}</strong> – {step.action}
          </p>

          {step.selector && (
            <p className="text-xs text-gray-500">
              <strong>Selector:</strong> {step.selector}
            </p>
          )}

          {step.input_value && (
            <p className="text-xs text-gray-500">
              <strong>Input:</strong> {step.input_value}
            </p>
          )}

          {step.url && (
            <p className="text-xs text-gray-500">
              <strong>URL:</strong> {step.url}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

/* -------------------------------------------------------
    JSON VIEW COMPONENT
------------------------------------------------------- */
function JsonView({ recording }: { recording: Recording }) {
  return (
    <pre className="bg-gray-900 text-green-300 text-xs p-4 rounded overflow-auto">
      {JSON.stringify(recording, null, 2)}
    </pre>
  );
}
