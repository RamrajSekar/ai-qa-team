"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/utils/api";
import type { Story } from "@/types/story";
import type { Recording } from "@/types/recorder";
import RecordingsTable from "@/components/recorder/RecordingsTable";
import RecordingViewer from "@/components/recorder/RecordingViewer";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function StoryDetailPage() {
  const params = useParams() as { projectId: string; storyId: string };
  const { projectId, storyId } = params;

  const [story, setStory] = useState<Story | null>(null);
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [viewRecording, setViewRecording] = useState<Recording | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadStory() {
    try {
      const res = await apiFetch(`/stories/${storyId}?project_id=${projectId}`);
      setStory(res.data);
    } catch (e) {
      console.error("Failed to load story:", e);
    }
  }

  async function loadRecordings() {
    try {
      const res = await apiFetch(`/recorder/by-story/${storyId}`);
      setRecordings(res.data || []);
    } catch (e) {
      console.error("Failed to load recordings:", e);
      setRecordings([]); // prevent map crash
    }
  }

  useEffect(() => {
    if (!storyId) return;
    setLoading(true);

    Promise.all([loadStory(), loadRecordings()]).finally(() =>
      setLoading(false)
    );
  }, [storyId]);

  if (loading) return <div className="p-6">Loading story…</div>;

  if (!story)
    return (
      <div className="p-6 text-red-500 font-medium">Story not found.</div>
    );

  return (
    <div className="p-6 space-y-8">
      {/* BACK BUTTON */}
        <div className="mb-4">
        <Link
            href={`/projects/${projectId}/stories`}
            className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition"
        >
            <ArrowLeft size={16} />
            Back to Stories
        </Link>
        </div>

      {/* STORY HEADER */}
      <div className="border rounded-lg p-5 bg-white shadow-sm">
        <h1 className="text-2xl font-semibold mb-2">{story.title}</h1>

        <p className="text-gray-600 mb-2">
          <strong>Description:</strong> {story.description || "—"}
        </p>

        <p className="text-gray-600 mb-2">
          <strong>Acceptance Criteria:</strong>{" "}
          {story.acceptance_criteria || "—"}
        </p>

        <p className="text-gray-600 mb-2">
          <strong>Out of Scope:</strong> {story.out_of_scope || "—"}
        </p>

        <p className="text-gray-500 text-sm">
          Created At: {new Date(story.created_at).toLocaleString()}
        </p>
      </div>

      {/* RECORDINGS TABLE */}
      <RecordingsTable
        recordings={recordings}
        onView={(rec) => setViewRecording(rec)}
      />

      {/* VIEWER MODAL */}
      {viewRecording && (
        <RecordingViewer
          open={true}
          recording={viewRecording}
          onClose={() => setViewRecording(null)}
        />
      )}
    </div>
  );
}
