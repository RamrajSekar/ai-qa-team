"use client";

import { Pencil, Trash2, PlayCircle, Eye } from "lucide-react";
import type { Story } from "@/types/story";

// -------------------------------
// Component Props typing
// -------------------------------
interface StoryCardProps {
  story: Story;
  onEdit: (story: Story) => void;
  onDelete: (story: Story) => void;
  onRecord: (story: Story) => void;
}

export default function StoryCard({
  story,
  onEdit,
  onDelete,
  onRecord,
}: StoryCardProps) {
  const hasRecording = !!story.recording_id;

  return (
    <div className="border rounded-lg p-4 bg-white shadow-sm hover:shadow-md transition">
      <h3 className="font-semibold text-lg">{story.title}</h3>

      {/* Description */}
      <p className="text-sm text-gray-600 mt-1 line-clamp-2">
        {story.description}
      </p>

      {/* Recording Status */}
      <div className="mt-2">
        {hasRecording ? (
          <span className="inline-block px-2 py-1 text-xs rounded bg-purple-100 text-purple-700">
            Recording Attached
          </span>
        ) : (
          <span className="inline-block px-2 py-1 text-xs rounded bg-gray-100 text-gray-500">
            No Recording
          </span>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 mt-4">
        {/* Record Button */}
        <button
          disabled={hasRecording}
          onClick={() => onRecord(story)}
          className={`flex items-center gap-1 px-3 py-1 rounded text-sm ${
            hasRecording
              ? "bg-gray-300 text-gray-600 cursor-not-allowed"
              : "bg-purple-600 text-white hover:bg-purple-700"
          }`}
        >
          <PlayCircle size={16} />
          {hasRecording ? "Recorded" : "Record"}
        </button>

        {/* Edit */}
        <button
          onClick={() => onEdit(story)}
          className="flex items-center gap-1 px-3 py-1 rounded bg-blue-100 text-blue-700 hover:bg-blue-200 text-sm"
        >
          <Pencil size={16} />
          Edit
        </button>

        {/* Delete */}
        <button
          onClick={() => onDelete(story)}
          className="flex items-center gap-1 px-3 py-1 rounded bg-red-100 text-red-700 hover:bg-red-200 text-sm"
        >
          <Trash2 size={16} />
          Delete
        </button>
      </div>
    </div>
  );
}
