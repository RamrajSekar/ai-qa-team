"use client";
import { useFeatures, FeatureGate } from "@/components/providers/FeatureFlagsProvider";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/utils/api";
import { Plus, Eye, Edit, Video } from "lucide-react";
import type { Story } from "@/types/story";
import StoryModal from "@/components/story/StoryModal";
import { WorkspaceDialog } from "@/components/ui/workspace-dialog";
import { DesignStats, DesignToolbar, DesignState, DesignBadge } from "@/components/projects/DesignWorkspace";
import RecorderOverlay from "@/components/recorder/RecorderOverlay";

export default function StoriesPage() {
  const { enabled } = useFeatures();
  const params = useParams() as { projectId: string };
  const { projectId } = params;

  const analysisEnabled = enabled("product_knowledge", "story_analysis");
  const [analyses, setAnalyses] = useState<Record<string, {state: string; finding_count: number; blocker_count: number}> | null>(null);
  const [analysisError, setAnalysisError] = useState(false);
  const analysisLabels: Record<string,string> = {not_analyzed:"Not analyzed",needs_review:"Findings need review",reviewed:"Reviewed",stale:"Stale"};
  const [stories, setStories] = useState<Story[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [openModal, setOpenModal] = useState(false);
  const [editStory, setEditStory] = useState<Story | null>(null);
  const [openRecorder, setOpenRecorder] = useState(false);
  const [recordStoryId, setRecordStoryId] = useState<string | null>(null);
  const [deleteStory, setDeleteStory] = useState<Story | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [query, setQuery] = useState("");
  const visibleStories = stories.filter(story => `${story.story_id} ${story.title} ${story.acceptance_criteria || ""}`.toLowerCase().includes(query.toLowerCase()));

  const loadStories = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    try {
      const res = await apiFetch(`/stories?project_id=${encodeURIComponent(projectId)}`);
      if (!res.ok) {
        throw new Error(`Could not load stories (HTTP ${res.status}).`);
      }
      if (!Array.isArray(res.data)) {
        throw new Error("The Stories API returned an unexpected response.");
      }
      setStories(res.data);
    } catch (error) {
      setStories([]);
      setLoadError(error instanceof Error ? error.message : "Could not load stories.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  async function handleDelete() {
    if (!deleteStory) return;

    setDeleting(true);

    setDeleteError("");
    try {
      const res = await apiFetch(`/stories/${encodeURIComponent(deleteStory.story_id)}?project_id=${encodeURIComponent(projectId)}`, { method: "DELETE" });
      if (!res.ok) throw new Error(typeof res.data?.detail === "string" ? res.data.detail : "Could not delete story. Please try again.");
      setDeleteStory(null);
      await loadStories();
    } catch (failure) { setDeleteError(failure instanceof Error ? failure.message : "Could not delete story."); }
    finally { setDeleting(false); }
  }

  useEffect(() => {
    if (projectId) void loadStories();
  }, [projectId, loadStories]);

  useEffect(() => {
    if (!analysisEnabled || !stories.length) return;
    const controller = new AbortController(); setAnalyses(null); setAnalysisError(false);
    const ids = stories.slice(0,100).map(item => item.story_id).join(",");
    void apiFetch(`/projects/${encodeURIComponent(projectId)}/knowledge/analysis-summaries?story_ids=${encodeURIComponent(ids)}`, {signal:controller.signal}).then(response => {
      if (!response.ok || !response.data || Array.isArray(response.data)) throw new Error("Unavailable");
      if (!controller.signal.aborted) setAnalyses(response.data);
    }).catch(() => {if (!controller.signal.aborted) setAnalysisError(true);});
    return () => controller.abort();
  }, [analysisEnabled, stories, projectId]);

  function handleEdit(story: Story) {
    setEditStory(story);
    setOpenModal(true);
  }

  function handleRecord(storyId: string) {
    setRecordStoryId(storyId);
    setOpenRecorder(true);
  }

  return (
    <div className="design-page">
      {/* Header */}
      <div className="workspace-page-header">
        <div><p className="workspace-eyebrow">Test design</p><h1>Stories</h1><p className="workspace-description">Define acceptance criteria, resolve ambiguity and design coverage.</p></div>

        <button
          onClick={() => {
            setEditStory(null);
            setOpenModal(true);
          }}
          className="workspace-button workspace-primary"
        >
          <Plus size={18} /> New Story
        </button>
      </div>

      {!loading && !loadError && <DesignStats items={[{ label: "Stories loaded", value: stories.length }, { label: "With acceptance criteria", value: stories.filter(item => item.acceptance_criteria?.trim()).length }, { label: "Need acceptance criteria", value: stories.filter(item => !item.acceptance_criteria?.trim()).length }]} />}
      <div className="design-guide"><strong>Start with a clear requirement</strong><p>Add acceptance criteria, review story analysis, then generate scenarios and detailed test cases.</p></div>
      <DesignToolbar query={query} onQuery={setQuery} placeholder="Search stories" />
      {/* Table */}
      {loading ? <p role="status">Loading stories…</p> : loadError ? (
        <div role="alert" className="space-y-2">
          <p>{loadError}</p>
          <button type="button" className="workspace-button" onClick={() => void loadStories()}>Try again</button>
        </div>
      ) : visibleStories.length === 0 ? <DesignState title={stories.length ? "No matching stories" : "No stories yet"}><p>{stories.length ? "Try a different title, ID or acceptance criterion." : "Select New Story to define your first requirement and acceptance criteria."}</p></DesignState> : (
      <div className="workspace-table-scroll design-table" role="region" aria-label="Story list; scroll horizontally for all columns" tabIndex={0}>
        <table className="w-full border-collapse">
          <thead className="bg-gray-100 text-left text-sm text-gray-600">
            <tr>
              <th className="p-3 border">Story ID</th>
              <th className="p-3 border">Title</th>
              <th className="p-3 border">Acceptance Criteria</th>
              <th className="p-3 border">Created At</th>{analysisEnabled && <th className="p-3 border">Story analysis</th>}
              <th className="p-3 border w-40 text-center">Actions</th>
            </tr>
          </thead>

          <tbody>
            {visibleStories.map((story) => (
              <tr key={story.story_id} className="hover:bg-gray-50">
                <td className="p-3 border font-medium">{story.story_id}</td>

                <td className="p-3 border">
                  <Link
                    href={`/projects/${projectId}/stories/${story.story_id}`}
                    className="text-indigo-600 hover:underline"
                  >
                    {story.title}
                  </Link>
                </td>

                <td className="p-3 border text-sm text-gray-700">
                  {story.acceptance_criteria ? <span className="design-excerpt">{story.acceptance_criteria}</span> : <DesignBadge tone="warning">Needs criteria</DesignBadge>}
                </td>

                <td className="p-3 border text-sm">
                  {new Date(story.created_at).toLocaleString()}
                </td>

                {analysisEnabled && <td className="p-3 border"><Link href={`/projects/${encodeURIComponent(projectId)}/stories/${encodeURIComponent(story.story_id)}#story-analysis`} className="design-back-link"><DesignBadge>{analysisError ? "Unavailable" : !analyses ? "Loading" : analysisLabels[analyses[story.story_id]?.state] || "Unavailable"}</DesignBadge></Link>{analyses?.[story.story_id] && <p>{analyses[story.story_id].finding_count} findings · {analyses[story.story_id].blocker_count} blockers</p>}</td>}
                <td className="p-3 border text-center">
                  <div className="flex items-center justify-center gap-2">

                    {/* VIEW */}
                    <Link
                      href={`/projects/${projectId}/stories/${story.story_id}`}
                      className="workspace-button"
                    >
                      <Eye size={14} /> View
                    </Link>

                    {/* EDIT */}
                    <button
                      onClick={() => handleEdit(story)}
                      className="workspace-button"
                    >
                      <Edit size={14} /> Edit
                    </button>
                    
                    {/* DELETE */}
                    <button
                      onClick={() => { setDeleteError(""); setDeleteStory(story); }}
                      className="workspace-button design-danger"
                    >
                      Delete
                    </button>

                    {/* RECORD */}
                    <FeatureGate names={["recorder"]}><button
                      onClick={() => handleRecord(story.story_id)}
                      className="px-2 py-1 text-xs bg-purple-600 text-white rounded hover:bg-purple-700 flex gap-1 items-center"
                    >
                      <Video size={14} /> Record
                    </button></FeatureGate>

                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      )}

      {/* MODAL */}
      <StoryModal
        open={openModal}
        onClose={() => setOpenModal(false)}
        onSaved={loadStories}
        projectId={projectId}
        story={editStory ?? undefined}
      />

      {/* RECORDER */}
      {enabled("recorder") && openRecorder && recordStoryId && (
        <RecorderOverlay
          url={`/projects/${projectId}/stories/${recordStoryId}`}
          storyId={recordStoryId}
          projectId={projectId}
          onClose={() => setOpenRecorder(false)}
        />
      )}

      {deleteStory && (
      <WorkspaceDialog open onClose={() => setDeleteStory(null)} title={`Delete story ${deleteStory.story_id}`} busy={deleting}>
        <div>
          <h3 className="text-lg font-semibold mb-2">
            Delete Story {deleteStory.story_id}?
          </h3>

          <p className="text-gray-600">
            Are you sure you want to delete this story? This action cannot be undone.
          </p>

          {deleteError && <p role="alert">{deleteError}</p>}
          <div className="flex justify-end mt-6 gap-3">
            <button
              className="workspace-button" disabled={deleting}
              onClick={() => setDeleteStory(null)}
            >
              Cancel
            </button>

            <button
              className="workspace-button design-danger"
              disabled={deleting}
              onClick={handleDelete}
            >
              {deleting ? "Deleting..." : "Delete"}
            </button>
          </div>
        </div>
      </WorkspaceDialog>
    )}
    </div>
  );
}
