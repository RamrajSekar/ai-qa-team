"use client";

import { apiFetch } from "@/utils/api";
import { useState } from "react";

interface DeleteProjectModalProps {
  open: boolean;
  onClose: () => void;
  projectId: string;
  projectName: string;
  onDeleted: () => void;
}

export default function DeleteProjectModal({
  open,
  onClose,
  projectId,
  projectName,
  onDeleted,
}: DeleteProjectModalProps) {
  const [confirmText, setConfirmText] = useState("");
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  const handleDelete = async () => {
    if (confirmText !== projectName) return;

    try {
      setLoading(true);

      const res = await apiFetch(`/projects/${projectId}`, {
        method: "DELETE",
      });

      if (res.ok) {
        onDeleted();
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white w-[420px] p-6 rounded-xl shadow-lg">
        <h2 className="text-lg font-semibold text-red-600">Delete Project</h2>

        <p className="text-sm text-gray-600 mt-2">
          This action is <strong>irreversible</strong>.  
          All stories, scenarios, testcases, environments & executions for:
        </p>

        <p className="font-semibold mt-3 text-gray-800">{projectName}</p>

        <p className="text-sm text-gray-500 mt-3">
          Type <span className="font-semibold">{projectName}</span> to confirm.
        </p>

        <input
          value={confirmText}
          onChange={(e) => setConfirmText(e.target.value)}
          className="mt-3 w-full border rounded-md p-2"
        />

        <div className="flex justify-end gap-2 mt-5">
          <button
            onClick={onClose}
            className="px-4 py-2 border rounded-md"
            disabled={loading}
          >
            Cancel
          </button>

          <button
            onClick={handleDelete}
            disabled={loading || confirmText !== projectName}
            className={`px-4 py-2 rounded-md text-white ${
              confirmText === projectName
                ? "bg-red-600 hover:bg-red-700"
                : "bg-red-300 cursor-not-allowed"
            }`}
          >
            {loading ? "Deleting..." : "Delete Project"}
          </button>
        </div>
      </div>
    </div>
  );
}
