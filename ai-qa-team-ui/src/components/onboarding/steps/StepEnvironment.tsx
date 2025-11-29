"use client";

import { useState, useEffect } from "react";
import StepFooter from "../StepFooter";
import { apiFetch } from "@/utils/api";
import { User } from "@/types/user";
import EnvironmentModal from "@/components/environment/EnvironmentModal";

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
  const [projectId, setProjectId] = useState<string | null>(null);
  const [openEnvModal, setOpenEnvModal] = useState(false);

  useEffect(() => {
    async function fetchProject() {
      const res = await apiFetch(`${process.env.NEXT_PUBLIC_API_URL}/projects`);
      if (res.ok) {
        const list = await res.json();
        if (list.length > 0) setProjectId(list[0].project_id);
      }
    }
    fetchProject();
  }, []);

  async function handleEnvSaved() {
    await apiFetch(`${process.env.NEXT_PUBLIC_API_URL}/onboarding/progress`, {
      method: "PUT",
      body: JSON.stringify({
        step_key: "environment",
        current_step: 3,
      }),
    });

    await refreshUser();
    next();
  }

  return (
    <div className="p-6">
      <h2 className="font-bold text-xl mb-4">Create Environment</h2>

      <p className="text-gray-500 mb-4">
        Add at least one environment (QA, Staging, Production).
      </p>

      <button
        className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
        onClick={() => setOpenEnvModal(true)}
        disabled={!projectId}
      >
        + Add Environment
      </button>

      <EnvironmentModal
        open={openEnvModal}
        mode="create"
        projectId={projectId ?? ""}
        env={null}
        onClose={() => setOpenEnvModal(false)}
        onSaved={handleEnvSaved}
      />

      <StepFooter onNext={next} onBack={back} />
    </div>
  );
}
