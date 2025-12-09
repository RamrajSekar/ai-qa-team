"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/utils/api";
import { X } from "lucide-react";

import type { Story } from "@/types/story";

interface StoryModalProps {
  open: boolean;
  onClose: () => void;
  onSaved: () => Promise<void>;
  projectId: string;
  story?: Story | null;
}

export default function StoryModal({
  open,
  onClose,
  onSaved,
  projectId,
  story,
}: StoryModalProps) {
  const isEdit = !!story;

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [acceptanceCriteria, setAcceptanceCriteria] = useState("");
  const [outOfScope, setOutOfScope] = useState("");
  const [saving, setSaving] = useState(false);

  // Load values in edit mode
  useEffect(() => {
    if (story) {
      setTitle(story.title || "");
      setDescription(story.description || "");
      setAcceptanceCriteria(story.acceptance_criteria || "");
      setOutOfScope(story.out_of_scope || "");
    } else {
      setTitle("");
      setDescription("");
      setAcceptanceCriteria("");
      setOutOfScope("");
    }
  }, [story]);

  if (!open) return null;

  async function handleSave() {
    if (!title.trim()) return;

    setSaving(true);

    const payload = {
      project_id: projectId,
      title,
      description,
      acceptance_criteria: acceptanceCriteria,
      out_of_scope: outOfScope,
    };

    let res;

    if (isEdit) {
      // Backend requires project_id in the query!
      res = await apiFetch(`/stories/${story!.story_id}?project_id=${projectId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    } else {
      res = await apiFetch(`/stories`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    }

    setSaving(false);

    if (!res.ok) {
      console.error("Story save failed", res);
      alert(res.data?.detail || "Failed to save story");
      return;
    }

    await onSaved();
    onClose();
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
      <div className="bg-white rounded-lg w-full max-w-2xl p-6 shadow-xl relative">

        {/* Close */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 text-gray-500 hover:text-black"
        >
          <X size={20} />
        </button>

        {/* Title */}
        <h2 className="text-xl font-semibold mb-4">
          {isEdit ? "Edit Story" : "Create New Story"}
        </h2>

        {/* Fields */}
        <div className="space-y-4">

          <div>
            <label className="font-medium text-sm">Title</label>
            <input
              className="w-full border p-2 rounded mt-1"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="User logs in successfully"
            />
          </div>

          <div>
            <label className="font-medium text-sm">Description</label>
            <textarea
              className="w-full border p-2 rounded mt-1"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </div>

          <div>
            <label className="font-medium text-sm">Acceptance Criteria</label>
            <textarea
              className="w-full border p-2 rounded mt-1"
              value={acceptanceCriteria}
              onChange={(e) => setAcceptanceCriteria(e.target.value)}
              rows={3}
            />
          </div>

          <div>
            <label className="font-medium text-sm">Out of Scope</label>
            <textarea
              className="w-full border p-2 rounded mt-1"
              value={outOfScope}
              onChange={(e) => setOutOfScope(e.target.value)}
              rows={3}
            />
          </div>
        </div>

        {/* Footer */}
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
            {saving ? "Saving…" : isEdit ? "Update Story" : "Create Story"}
          </button>
        </div>

      </div>
    </div>
  );
}
