"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/utils/api";

interface EditProjectModalProps {
  open: boolean;
  onClose: () => void;
  project: {
    project_id: string;
    name: string;
    description?: string;
  };
  onUpdated: () => void | Promise<void>;
}

export default function EditProjectModal({
  open,
  onClose,
  project,
  onUpdated,
}: EditProjectModalProps) {
  const [name, setName] = useState(project?.name || "");
  const [description, setDescription] = useState(project?.description || "");
  const [loading, setLoading] = useState(false);
  // Reset fields when modal opens
  useEffect(() => {
    if (project) {
      setName(project.name || "");
      setDescription(project.description || "");
    }
  }, [project, open]);

  if (!open || !project) return null;

  const handleSave = async () => {
    try {
      setLoading(true);

      const res = await apiFetch(`/projects/${project.project_id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name,
          description,
        }),
      });

      if (res.ok) {
        await onUpdated();
        // refresh the global project list
        if (typeof window !== "undefined") {
          window.dispatchEvent(new Event("projects-updated"));
        }
        onClose();
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white p-6 rounded-xl shadow-lg w-[420px]">
        <h2 className="text-lg font-semibold mb-4">Edit Project</h2>

        {/* Project Name */}
        <label className="text-sm font-medium">Project Name</label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full border rounded-md p-2 mt-1 mb-4"
          placeholder="Enter project name"
        />

        {/* Description */}
        <label className="text-sm font-medium">Description</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full border rounded-md p-2 mt-1"
          rows={3}
          placeholder="Optional description..."
        />

        <div className="flex justify-end gap-2 mt-5">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 border rounded-md"
          >
            Cancel
          </button>

          <button
            onClick={handleSave}
            disabled={loading}
            className="px-4 py-2 bg-purple-600 text-white rounded-md"
          >
            {loading ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
