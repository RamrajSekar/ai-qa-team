"use client";

import { apiFetch } from "@/utils/api";
import { X } from "lucide-react";
import { useState } from "react";

interface DeleteStoryModalProps {
  open: boolean;
  onClose: () => void;
  storyId: string;
  projectId: string;
  onDeleted: () => Promise<void>;
}

export default function DeleteStoryModal({
  open,
  onClose,
  storyId,
  projectId,
  onDeleted,
}: DeleteStoryModalProps) {
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  async function handleDelete() {
    setLoading(true);

    const res = await apiFetch(`/stories/${storyId}&project_id=${projectId}`, {
      method: "DELETE",
    });

    setLoading(false);

    if (!res.ok) {
      console.error("Failed to delete story", res);
      return;
    }

    await onDeleted(); // refresh list
    onClose();         // close modal AFTER refresh
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
      <div className="bg-white rounded-lg max-w-md w-full p-6 shadow-xl relative">

        {/* Close */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 text-gray-500 hover:text-black"
        >
          <X size={20} />
        </button>

        <h2 className="text-xl font-semibold mb-4">Delete Story?</h2>

        <p className="text-gray-600 mb-6">
          This action cannot be undone. This will permanently remove the story
          and its associated scenarios and testcases.
        </p>

        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 border rounded"
          >
            Cancel
          </button>

          <button
            onClick={handleDelete}
            disabled={loading}
            className={`px-4 py-2 rounded text-white ${
              loading ? "bg-gray-400" : "bg-red-600 hover:bg-red-700"
            }`}
          >
            {loading ? "Deleting..." : "Delete"}
          </button>
        </div>

      </div>
    </div>
  );
}
