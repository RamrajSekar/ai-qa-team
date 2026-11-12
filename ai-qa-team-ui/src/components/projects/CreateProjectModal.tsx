"use client";

import { useState } from "react";
import { WorkspaceDialog } from "@/components/ui/workspace-dialog";
import { apiFetch } from "@/utils/api";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: () => Promise<void>; // reload project list
  createdBy: string; // user email
}

export default function CreateProjectModal({
  open,
  onClose,
  onCreated,
  createdBy,
}: Props) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!open) return null;

  async function submit() {
    setError("");
    if (!name.trim()) {
      setError("Project name is required.");
      return;
    }

    setLoading(true);

    const body = {
      name,
      description,
      created_by: createdBy,
    };

    try {
      const res = await apiFetch("/projects", { method: "POST", body: JSON.stringify(body) });
      if (!res.ok) throw new Error(typeof res.data?.detail === "string" ? res.data.detail : "Could not create project.");
      setName(""); setDescription("");
      await onCreated(); onClose();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not reach the project service. Try again.");
    } finally { setLoading(false); }
  }

  return (
    <WorkspaceDialog open={open} onClose={onClose} title="Create New Project" busy={loading}>

        {/* Title */}
        <h2 className="text-xl font-semibold mb-4">
          Create New Project
        </h2>

        {/* Name */}
        <label htmlFor="new-project-name" className="text-sm font-medium">Project Name</label>
        <input id="new-project-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full mt-1 mb-4 p-2 rounded-md border"
          placeholder="Customer portal"
        />

        {/* Description */}
        <label htmlFor="new-project-description" className="text-sm font-medium">Description</label>
        <textarea id="new-project-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full mt-1 p-2 h-24 rounded-md border"
          placeholder="Short description about this project"
        />

        {error && (
          <p className="text-red-500 text-sm mt-3">{error}</p>
        )}

        {/* Footer */}
        <div className="mt-6 flex justify-end gap-3">
          <button
            className="px-4 py-2 bg-gray-200 rounded-md"
            onClick={onClose}
          >
            Cancel
          </button>

          <button
            onClick={submit}
            disabled={loading}
            className="px-5 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
          >
            {loading ? "Creating..." : "Create Project"}
          </button>
        </div>
    </WorkspaceDialog>
  );
}
