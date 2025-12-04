"use client";

import { useState, useEffect } from "react";
import StepFooter from "../StepFooter";
import { useProjects } from "@/hooks/useProjects";
import EnvironmentModal from "@/components/environment/EnvironmentModal";
import { apiFetch } from "@/utils/api";
import { User } from "@/types/user";

interface StepEnvironmentProps {
  user: User;
  refreshUser: () => Promise<void>;
  next: () => void;
  back: () => void;
}

export default function StepEnvironment({
  user,
  refreshUser,
  next,
  back,
}: StepEnvironmentProps) {
  const [openEnvModal, setOpenEnvModal] = useState(false);
  const [projectId, setProjectId] = useState<string | null>(null);

  const { projects, loading: loadingProjects, reload } = useProjects();

  // --------------------------------------------
  // 1. Auto-select project for onboarding
  // --------------------------------------------
  useEffect(() => {
    if (projects.length > 0) {
      // Best UX: select most recently created project
      const last = projects[projects.length - 1];
      setProjectId(last.project_id);
    }
  }, [projects]);

  // --------------------------------------------
  // 2. Handle environment creation → mark onboarding step
  // --------------------------------------------
  async function handleEnvSaved() {
    // Update onboarding progress
    await apiFetch("/onboarding/progress", {
      method: "PUT",
      body: JSON.stringify({
        step_key: "environment",
        current_step: 3,
      }),
    });

    await refreshUser();
    next();
  }

  // --------------------------------------------
  // Render UI
  // --------------------------------------------
  return (
    <div className="p-6">
      <h2 className="font-bold text-xl mb-4">Create Your First Environment</h2>

      <p className="text-gray-500 mb-4">
        Environments help control URLs, credentials, auth tokens & variables for
        each deployment stage (QA, Staging, Production).
      </p>

      {/* Loading projects */}
      {loadingProjects && (
        <p className="text-gray-400 text-sm mb-4">Loading projects...</p>
      )}

      {!projectId && !loadingProjects && (
        <p className="text-red-500 text-sm mb-4">
          No project found — go back and create one first.
        </p>
      )}

      <button
        className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
        onClick={() => setOpenEnvModal(true)}
        disabled={!projectId}
      >
        + Add Environment
      </button>

      {/* ENVIRONMENT MODAL */}
      <EnvironmentModal
        open={openEnvModal}
        mode="create"
        projectId={projectId ?? ""}
        env={null}
        onClose={() => setOpenEnvModal(false)}
        onSaved={handleEnvSaved}
      />

      {/* FOOTER NAVIGATION */}
      <StepFooter onNext={next} onBack={back} />
    </div>
  );
}
