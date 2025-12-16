"use client";

import { useState, useEffect } from "react";
import { X } from "lucide-react";
import { apiFetch } from "@/utils/api";
import type { Scenario } from "@/types/scenario";

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
  const isEdit = !!scenario;

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState("pending");
  const [saving, setSaving] = useState(false);

  /** Load scenario data when editing */
  useEffect(() => {
    if (scenario) {
      setTitle(scenario.title || "");
      setDescription(scenario.description || "");
      setStatus(scenario.status || "pending");
    } else {
      setTitle("");
      setDescription("");
      setStatus("pending");
    }
  }, [scenario]);

  if (!open) return null;

  /** Save or Update */
  async function handleSave() {
    if (!title.trim()) return;

    setSaving(true);

    const payload = {
      story_id: storyId,
      title,
      description,
      status,
      steps: scenario?.steps || [], // keep existing steps for now
    };

    const url = isEdit
      ? `/scenarios/${scenario?.scenario_id}?project_id=${projectId}`
      : `/scenarios?story_id=${storyId}&project_id=${projectId}`;

    const method = isEdit ? "PATCH" : "POST";

    const res = await apiFetch(url, {
      method,
      body: JSON.stringify(payload),
    });

    setSaving(false);

    if (!res.ok) {
      console.error("Scenario save failed", res);
      return;
    }

    await onSaved();
    onClose();
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
      <div className="bg-white rounded-lg w-full max-w-2xl p-6 shadow-xl relative">
        
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 text-gray-500 hover:text-black"
        >
          <X size={20} />
        </button>

        <h2 className="text-xl font-semibold mb-4">
          {isEdit ? "Edit Scenario" : "Create Scenario"}
        </h2>

        <div className="space-y-4">
          
          {/* Title */}
          <div>
            <label className="font-medium text-sm">Title</label>
            <input
              className="w-full border p-2 rounded mt-1"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="User logs in and sees dashboard"
            />
          </div>

          {/* Description */}
          <div>
            <label className="font-medium text-sm">Description</label>
            <textarea
              className="w-full border p-2 rounded mt-1"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          {/* Status */}
          <div>
            <label className="font-medium text-sm">Status</label>
            <select
              className="w-full border p-2 rounded mt-1"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="pending">Pending</option>
              <option value="draft">Draft</option>
              <option value="approved">Approved</option>
            </select>
          </div>

          {/* FUTURE: Steps, Complexity, Approval flags */}
        </div>

        <div className="flex justify-end mt-6 gap-3">
          <button onClick={onClose} className="px-4 py-2 border rounded">
            Cancel
          </button>

          <button
            onClick={handleSave}
            disabled={saving || !title.trim()}
            className={`px-4 py-2 rounded text-white ${
              saving || !title.trim()
                ? "bg-gray-400 cursor-not-allowed"
                : "bg-purple-600 hover:bg-purple-700"
            }`}
          >
            {saving ? "Saving..." : "Save Scenario"}
          </button>
        </div>
      </div>
    </div>
  );
}
