"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/utils/api";
import { Plus, Eye, Edit, Video } from "lucide-react";
import type { Story } from "@/types/story";
import StoryModal from "@/components/story/StoryModal";
import RecorderOverlay from "@/components/recorder/RecorderOverlay";

export default function StoriesPage() {
  const params = useParams() as { projectId: string };
  const { projectId } = params;

  const [stories, setStories] = useState<Story[]>([]);
  const [loading, setLoading] = useState(true);
  const [openModal, setOpenModal] = useState(false);
  const [editStory, setEditStory] = useState<Story | null>(null);
  const [openRecorder, setOpenRecorder] = useState(false);
  const [recordStoryId, setRecordStoryId] = useState<string | null>(null);

  async function loadStories() {
    try {
      setLoading(true);
      const res = await apiFetch(`/stories?project_id=${projectId}`);
      setStories(res.data || []);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (projectId) loadStories();
  }, [projectId]);

  function handleEdit(story: Story) {
    setEditStory(story);
    setOpenModal(true);
  }

  function handleRecord(storyId: string) {
    setRecordStoryId(storyId);
    setOpenRecorder(true);
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Stories</h1>

        <button
          onClick={() => {
            setEditStory(null);
            setOpenModal(true);
          }}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-md shadow hover:bg-indigo-700 transition"
        >
          <Plus size={18} /> New Story
        </button>
      </div>

      {/* Table */}
      <div className="overflow-hidden border rounded-lg bg-white shadow-sm">
        <table className="w-full border-collapse">
          <thead className="bg-gray-100 text-left text-sm text-gray-600">
            <tr>
              <th className="p-3 border">Story ID</th>
              <th className="p-3 border">Title</th>
              <th className="p-3 border">Acceptance Criteria</th>
              <th className="p-3 border">Created At</th>
              <th className="p-3 border w-40 text-center">Actions</th>
            </tr>
          </thead>

          <tbody>
            {stories.map((story) => (
              <tr key={story.story_id} className="hover:bg-gray-50">
                <td className="p-3 border font-medium">{story.story_id}</td>

                <td className="p-3 border">
                  <a
                    href={`/projects/${projectId}/stories/${story.story_id}`}
                    className="text-indigo-600 hover:underline"
                  >
                    {story.title}
                  </a>
                </td>

                <td className="p-3 border text-sm text-gray-700">
                  {story.acceptance_criteria?.substring(0, 50) || "—"}
                </td>

                <td className="p-3 border text-sm">
                  {new Date(story.created_at).toLocaleString()}
                </td>

                <td className="p-3 border text-center">
                  <div className="flex items-center justify-center gap-2">

                    {/* VIEW */}
                    <a
                      href={`/projects/${projectId}/stories/${story.story_id}`}
                      className="px-2 py-1 text-xs bg-gray-200 rounded hover:bg-gray-300 flex gap-1 items-center"
                    >
                      <Eye size={14} /> View
                    </a>

                    {/* EDIT */}
                    <button
                      onClick={() => handleEdit(story)}
                      className="px-2 py-1 text-xs bg-gray-100 border rounded hover:bg-gray-200 flex gap-1 items-center"
                    >
                      <Edit size={14} /> Edit
                    </button>

                    {/* RECORD */}
                    <button
                      onClick={() => handleRecord(story.story_id)}
                      className="px-2 py-1 text-xs bg-purple-600 text-white rounded hover:bg-purple-700 flex gap-1 items-center"
                    >
                      <Video size={14} /> Record
                    </button>

                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* MODAL */}
      <StoryModal
        open={openModal}
        onClose={() => setOpenModal(false)}
        onSaved={loadStories}
        projectId={projectId}
        story={editStory ?? undefined}
      />

      {/* RECORDER */}
      {openRecorder && recordStoryId && (
        <RecorderOverlay
          url={`/projects/${projectId}/stories/${recordStoryId}`}
          storyId={recordStoryId}
          projectId={projectId}
          onClose={() => setOpenRecorder(false)}
        />
      )}
    </div>
  );
}
