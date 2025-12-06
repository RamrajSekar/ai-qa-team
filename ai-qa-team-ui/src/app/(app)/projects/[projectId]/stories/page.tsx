'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { apiFetch } from '@/utils/api';
import { Plus } from 'lucide-react';
import type { Story } from "@/types/story";
import StoryModal from "@/components/story/StoryModal";

export default function StoriesPage() {
  const params = useParams() as { projectId: string };
  const { projectId } = params;
  
  const [stories, setStories] = useState<Story[]>([]);
  const [loading, setLoading] = useState(true);
  const [openModal, setOpenModal] = useState(false);

  async function loadStories() {
    try {
      setLoading(true);

      const res = await apiFetch(`/stories?project_id=${projectId}`);
      console.log("Stories API response:", res.data);
      setStories(res.data || []);
    } catch (err) {
      console.error('Failed to fetch stories:', err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (projectId) loadStories();
  }, [projectId]);

  if (loading) {
    return <div className="p-6 text-gray-600">Loading stories…</div>;
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Stories</h1>

        <button
          onClick={() => setOpenModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-md shadow hover:bg-indigo-700 transition"
        >
          <Plus size={18} /> New Story
        </button>
      </div>

      {/* Stories List */}
      {stories.length === 0 ? (
        <div className="p-4 border rounded-md bg-gray-50 text-gray-500">
          No stories created yet.
        </div>
      ) : (
        <div className="space-y-3">
          {stories.map((story) => (
            <a
              key={story.story_id}
              href={`/projects/${projectId}/stories/${story.story_id}`}
              className="block p-4 border rounded-md bg-white hover:shadow transition"
            >
              <p className="font-medium">{story.title}</p>

              <p className="text-sm text-gray-500 mt-1">
                {story.description || "No description"}
              </p>

              <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                {story.acceptance_criteria || "No Acceptance Criteria"}
              </p>
            </a>
          ))}
        </div>
      )}

      {/* NEW STORY MODAL */}
      <StoryModal
        open={openModal}
        onClose={() => setOpenModal(false)}
        onSaved={loadStories}
        projectId={projectId}
      />
    </div>
  );
}
