"use client";
import { useFeatures, FeatureGate } from "@/components/providers/FeatureFlagsProvider";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { apiFetch } from "@/utils/api";

import type { Story } from "@/types/story";
import type { Recording } from "@/types/recorder";

import RecordingsTable from "@/components/recorder/RecordingsTable";
import RecordingViewer from "@/components/recorder/RecordingViewer";
import RecorderOverlay from "@/components/recorder/RecorderOverlay";

import type { Scenario } from "@/types/scenario";
import ScenarioTable from "@/components/scenarios/ScenarioTable";
import ScenarioModal from "@/components/scenarios/ScenarioModal";
import ScenarioViewer from "@/components/scenarios/ScenarioViewer";

export default function StoryDetailsPage() {
  const { enabled } = useFeatures();
  const recorderEnabled = enabled("recorder");
  const scenariosEnabled = enabled("scenario_generation");
  const params = useParams() as { projectId: string; storyId: string };
  const { projectId, storyId } = params;

  const [story, setStory] = useState<Story | null>(null);
  const [loading, setLoading] = useState(true);

  // Recorder
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [viewRecording, setViewRecording] = useState<Recording | null>(null);
  const [openRecorder, setOpenRecorder] = useState(false);

  // Scenarios
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [scenarioModalOpen, setScenarioModalOpen] = useState(false);
  const [editingScenario, setEditingScenario] = useState<Scenario | undefined>();
  const [viewScenario, setViewScenario] = useState<Scenario | null>(null);

  // -----------------------------
  // LOAD STORY
  // -----------------------------
  async function loadStory() {
    try {
      const res = await apiFetch(`/stories/${storyId}?project_id=${projectId}`);
      if (res.ok) setStory(res.data);
    } catch (err) {
      console.error("Failed to load story:", err);
    }
  }

  // -----------------------------
  // LOAD RECORDINGS
  // -----------------------------
  async function loadRecordings() {
    if (!recorderEnabled) return;
    try {
      const res = await apiFetch(`/recorder/by-story/${storyId}`);
      setRecordings(res.data || []);
    } catch (err) {
      console.error("Failed to load recordings:", err);
      setRecordings([]);
    }
  }

  // -----------------------------
  // LOAD SCENARIOS
  // -----------------------------
  async function loadScenarios() {
    if (!scenariosEnabled) return;
    try {
      const res = await apiFetch(
        `/scenarios?story_id=${storyId}&project_id=${projectId}`
      );
      setScenarios(res.data || []);
    } catch (err) {
      console.error("Failed to load scenarios:", err);
      setScenarios([]);
    }
  }

  // -----------------------------
  // INITIAL LOAD
  // -----------------------------
  useEffect(() => {
    if (!storyId) return;

    setLoading(true);

    Promise.all([loadStory(), loadRecordings(), loadScenarios()]).finally(() =>
      setLoading(false)
    );
  }, [storyId, recorderEnabled, scenariosEnabled]);

  if (loading) return <div className="p-6">Loading story…</div>;

  if (!story)
    return (
      <div className="p-6 text-red-500 font-medium">Story not found.</div>
    );

  return (
    <div className="p-6 space-y-10">

      {/* BACK BUTTON */}
      <Link
        href={`/projects/${projectId}/stories`}
        className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
      >
        <ArrowLeft size={16} />
        Back to Stories
      </Link>

      {/* STORY HEADER */}
      <div className="border rounded-lg p-5 bg-white shadow-sm">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold">{story.title}</h1>

            {story.description && (
              <p className="text-gray-700 mt-1">{story.description}</p>
            )}

            <div className="mt-3 space-y-1 text-gray-600">
              <p>
                <strong>Acceptance Criteria:</strong>{" "}
                {story.acceptance_criteria || "—"}
              </p>
              <p>
                <strong>Out of Scope:</strong> {story.out_of_scope || "—"}
              </p>

              <p className="text-sm text-gray-500">
                Created At: {new Date(story.created_at).toLocaleString()}
              </p>
            </div>
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

      {/* SCENARIOS SECTION */}
      <FeatureGate names={["scenario_generation"]}><div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Scenarios</h2>

          <button
            onClick={() => {
              setEditingScenario(undefined);
              setScenarioModalOpen(true);
            }}
            className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
          >
            + Add Scenario
          </button>
        </div>

        <ScenarioTable
          scenarios={scenarios}
          onView={(s) => setViewScenario(s)}
          onEdit={(s) => {
            setEditingScenario(s);
            setScenarioModalOpen(true);
          }}
          onDelete={async (s) => {
            if (!confirm(`Delete scenario "${s.title}"?`)) return;
            await apiFetch(`/scenarios/${s.scenario_id}?project_id=${projectId}`, {
              method: "DELETE",
            });
            loadScenarios();
          }}
        />
      </div>

      </FeatureGate>

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

      {/* VIEW SCENARIO MODAL */}
      {scenariosEnabled && viewScenario && (
        <ScenarioViewer
          open={true}
          scenario={viewScenario}
          onClose={() => setViewScenario(null)}
        />
      )}

      {/* CREATE / EDIT SCENARIO MODAL */}
      <FeatureGate names={["scenario_generation"]}><ScenarioModal
        open={scenarioModalOpen}
        onClose={() => setScenarioModalOpen(false)}
        onSaved={loadScenarios}
        projectId={projectId}
        storyId={storyId}
        scenario={editingScenario}
      /></FeatureGate>

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
