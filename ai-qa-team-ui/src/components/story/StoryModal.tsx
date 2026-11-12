"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/utils/api";
import { WorkspaceDialog } from "@/components/ui/workspace-dialog";

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
  const [saveError, setSaveError] = useState("");

  // Load values in edit mode
  useEffect(() => {
    setSaveError("");
    if (!open) return;
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
  }, [open, story]);

  if (!open) return null;

  async function handleSave() {
    if (!title.trim()) return;

    setSaving(true);
    setSaveError("");

    const payload = {
      project_id: projectId,
      title,
      description,
      acceptance_criteria: acceptanceCriteria,
      out_of_scope: outOfScope,
    };

    try {
      const path = story
        ? `/stories/${encodeURIComponent(story.story_id)}?project_id=${encodeURIComponent(projectId)}`
        : "/stories";
      const res = await apiFetch(path, {
        method: isEdit ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const detail = res.data?.detail;
        setSaveError(`Could not save story (HTTP ${res.status}).${typeof detail === "string" ? ` ${detail}` : ""}`);
        return;
      }
    } catch {
      setSaveError("Could not reach the Stories API. Check the connection and try again.");
      return;
    } finally {
      setSaving(false);
    }

    onClose();
    await onSaved();
  }

  return (
    <WorkspaceDialog open={open} onClose={onClose} title={isEdit ? "Edit Story" : "Create New Story"} busy={saving} className="workspace-dialog-wide">

        {/* Title */}
        <h2 className="text-xl font-semibold mb-4">
          {isEdit ? "Edit Story" : "Create New Story"}
        </h2>
        {saveError && <p role="alert" className="mb-3 text-sm text-red-700">{saveError}</p>}

        {/* Fields */}
        <div className="space-y-4">

          <div>
            <label htmlFor="story-title" className="font-medium text-sm">Title</label>
            <input id="story-title"
              className="w-full border p-2 rounded mt-1"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="User logs in successfully"
            />
          </div>

          <div>
            <label htmlFor="story-description" className="font-medium text-sm">Description</label>
            <textarea id="story-description"
              className="w-full border p-2 rounded mt-1"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </div>

          <div>
            <label htmlFor="story-acceptance-criteria" className="font-medium text-sm">Acceptance Criteria</label>
            <textarea id="story-acceptance-criteria"
              className="w-full border p-2 rounded mt-1"
              value={acceptanceCriteria}
              onChange={(e) => setAcceptanceCriteria(e.target.value)}
              rows={3}
            />
          </div>

          <div>
            <label htmlFor="story-out-of-scope" className="font-medium text-sm">Out of Scope</label>
            <textarea id="story-out-of-scope"
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

    </WorkspaceDialog>
  );
}
