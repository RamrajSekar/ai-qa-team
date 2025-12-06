'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { apiFetch } from '@/utils/api';
import RecorderOverlay from '@/components/recorder/RecorderOverlay';
import { Play, Plus } from 'lucide-react';
import type { Story } from "@/types/story";
import type { TestCase } from "@/types/testcase";


export default function StoryDetailPage() {
  const params = useParams() as { projectId: string; storyId: string };

  const { projectId, storyId } = params;

  const [story, setStory] = useState<Story | null>(null);
  const [testcases, setTestcases] = useState<TestCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [openRecorder, setOpenRecorder] = useState(false);

  async function loadStory() {
    try {
      setLoading(true);

      const res = await apiFetch(`/stories/${storyId}?project_id=${projectId}`);
      console.log("Stories[story] API response:", res.data);
      setStory(res.data || null);

    //   const tc = await apiFetch(`/testcases?story_id=${storyId}&project_id=${projectId}`);
    //   setTestcases(tc.data || null);
    } catch (err) {
      console.error('Failed to load story details:', err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (storyId) loadStory();
  }, [storyId]);

  if (loading) {
    return (
      <div className="p-6 text-gray-600 animate-pulse">
        Loading story details…
      </div>
    );
  }

  if (!story) {
    return (
      <div className="p-6 text-red-500">
        Story not found.
      </div>
    );
  }

  return (
    <div className="p-6 space-y-8">

      {/* Breadcrumb */}
      <div className="text-sm text-gray-500">
        <Link href={`/projects/${projectId}`} className="hover:underline">
          Project
        </Link>
        {' / '}
        <span className="font-semibold text-gray-700">{story.title}</span>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{story.title}</h1>
          <p className="text-gray-600 mt-1">{story.description}</p>
        </div>

        <button
          onClick={() => setOpenRecorder(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-md shadow hover:bg-indigo-700 transition"
        >
          <Plus size={18} /> Record Steps
        </button>
      </div>

      {/* Acceptance Criteria */}
      <div className="bg-gray-50 p-4 rounded-md border">
        <h3 className="font-semibold mb-2">Acceptance Criteria</h3>
        <pre className="whitespace-pre-wrap text-gray-700">
          {story.acceptance_criteria || "No acceptance criteria provided."}
        </pre>
      </div>

      {/* Out of Scope */}
      <div className="bg-gray-50 p-4 rounded-md border">
        <h3 className="font-semibold mb-2">Out of Scope</h3>
        <pre className="whitespace-pre-wrap text-gray-700">
          {story.out_of_scope || "No out-of-scope items defined."}
        </pre>
      </div>

      {/* Test Cases Section */}
      <div className="mt-2">
        <h2 className="text-lg font-semibold mb-3">Test Cases</h2>

        {testcases.length === 0 ? (
          <div className="p-4 border rounded-md text-gray-500 bg-gray-50">
            No test cases created yet.
          </div>
        ) : (
          <div className="space-y-3">
            {testcases.map((tc) => (
              <Link
                key={tc.testcase_id}
                href={`/projects/${projectId}/stories/${storyId}/testcases/${tc.testcase_id}`}
                className="block p-4 border rounded-md bg-white hover:shadow transition"
              >
                <div className="flex items-center justify-between">
                  <p className="font-medium">{tc.title}</p>
                  <Play size={18} className="text-indigo-600" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Recorder Overlay */}
      {openRecorder && (
        <RecorderOverlay
          url={`/projects/${projectId}/stories/${storyId}`}
          storyId={storyId}
          projectId={projectId}
          onClose={() => setOpenRecorder(false)}
        />
      )}
    </div>
  );
}
