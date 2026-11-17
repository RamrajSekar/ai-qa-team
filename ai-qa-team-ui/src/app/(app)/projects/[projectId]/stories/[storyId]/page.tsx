"use client";
import { useFeatures, FeatureGate } from "@/components/providers/FeatureFlagsProvider";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { apiFetch } from "@/utils/api";

import type { Story } from "@/types/story";
import type { Recording } from "@/types/recorder";

import RecordingsTable from "@/components/recorder/RecordingsTable";
import RecordingViewer from "@/components/recorder/RecordingViewer";
import RecorderOverlay from "@/components/recorder/RecorderOverlay";

import StoryAnalysisPanel from "@/components/knowledge/StoryAnalysisPanel";

export default function StoryDetailsPage() {
  const { enabled } = useFeatures();
  const recorderEnabled = enabled("recorder");
  const params = useParams() as { projectId: string; storyId: string };
  const { projectId, storyId } = params;

  const [story, setStory] = useState<Story | null>(null);
  const [loading, setLoading] = useState(true);
  const [storyError, setStoryError] = useState("");

  // Recorder
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [viewRecording, setViewRecording] = useState<Recording | null>(null);
  const [openRecorder, setOpenRecorder] = useState(false);

  // -----------------------------
  // LOAD STORY
  // -----------------------------
  const loadStory = useCallback(async () => {
    setStoryError("");
    try {
      const res = await apiFetch(`/stories/${storyId}?project_id=${projectId}`);
      if (!res.ok) throw new Error(res.status === 404 ? "Story not found or unavailable." : "Could not load this story.");
      setStory(res.data);
    } catch (err) {
      setStoryError(err instanceof Error ? err.message : "Could not load this story.");
    }
  }, [storyId, projectId]);

  // -----------------------------
  // LOAD RECORDINGS
  // -----------------------------
  const loadRecordings = useCallback(async () => {
    if (!recorderEnabled) return;
    try {
      const res = await apiFetch(`/recorder/by-story/${storyId}`);
      setRecordings(res.data || []);
    } catch (err) {
      console.error("Failed to load recordings:", err);
      setRecordings([]);
    }
  }, [recorderEnabled, storyId]);

  // -----------------------------
  // INITIAL LOAD
  // -----------------------------
  useEffect(() => {
    if (!storyId) return;

    setLoading(true);

    Promise.all([loadStory(), loadRecordings()]).finally(() =>
      setLoading(false)
    );
  }, [storyId, loadStory, loadRecordings]);

  if (loading) return <div className="p-6">Loading story…</div>;

  if (storyError) return <div className="design-state" role="alert"><strong>{storyError}</strong><button className="workspace-button" onClick={() => void loadStory()}>Try again</button></div>;

  if (!story)
    return (
      <div className="p-6 text-red-500 font-medium">Story not found.</div>
    );

  return (
    <div className="design-page">

      {/* BACK BUTTON */}
      <Link
        href={`/projects/${projectId}/stories`}
        className="design-back-link inline-flex items-center gap-2"
      >
        <ArrowLeft size={16} />
        Back to Stories
      </Link>

      {/* STORY HEADER */}
      <div className="design-story-summary">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="workspace-eyebrow">Story · {story.story_id}</p><h1>{story.title}</h1>

            {story.description && (
              <p className="text-gray-700 mt-1">{story.description}</p>
            )}

            <div className="design-story-fields">
              <div><h2>Acceptance criteria</h2><p>{story.acceptance_criteria || "No acceptance criteria yet. Add explicit expectations before generating tests."}</p></div>
              <div><h2>Out of scope</h2><p>{story.out_of_scope || "Not specified"}</p></div>
            </div>
            <p className="workspace-metadata">Created {story.created_at ? new Date(story.created_at).toLocaleString() : "date not recorded"}</p>
          </div>

          {/* RECORD BUTTON */}
          <FeatureGate names={["recorder"]}><button
            onClick={() => setOpenRecorder(true)}
            className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
          >
            Record Steps
          </button></FeatureGate>
        </div>
      </div>

      <FeatureGate names={["product_knowledge", "story_analysis"]}><StoryAnalysisPanel key={`${projectId}:${storyId}`} projectId={projectId} storyId={storyId} /></FeatureGate>

      <FeatureGate names={["scenario_generation"]}><section className="workspace-card p-5 flex flex-wrap items-center justify-between gap-3"><div><h2>Scenarios</h2><p>Generate and review scenarios for this story.</p></div><Link className="workspace-button workspace-primary" href={`/projects/${projectId}/scenarios?story_id=${encodeURIComponent(storyId)}`}>Open Scenarios</Link></section></FeatureGate>

      {/* RECORDINGS SECTION */}
      <FeatureGate names={["recorder"]}>
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Recordings</h2>

        <RecordingsTable
          recordings={recordings}
          onView={(rec) => setViewRecording(rec)}
        />
      </div>

      </FeatureGate>

      {/* VIEW RECORDING MODAL */}
      {recorderEnabled && viewRecording && (
        <RecordingViewer
          open={true}
          recording={viewRecording}
          onClose={() => setViewRecording(null)}
        />
      )}

      {/* RECORDER OVERLAY */}
      {recorderEnabled && openRecorder && (
        <RecorderOverlay
          url="/" // TODO: Replace when environment URL selection is added
          storyId={storyId}
          projectId={projectId}
          onClose={() => setOpenRecorder(false)}
        />
      )}
    </div>
  );
}
