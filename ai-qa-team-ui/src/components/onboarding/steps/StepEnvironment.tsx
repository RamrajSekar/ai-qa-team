"use client";

import { useState } from "react";
import StepFooter from "../StepFooter";
import EnvironmentModal from "@/components/environment/EnvironmentModal";
import StepLayout from "../StepLayout";

interface StepEnvironmentProps {
  projectId: string | null;
  refreshUser: () => Promise<void>;
  next: () => void;
  back: () => void;
}

export default function StepEnvironment({
  projectId,
  refreshUser,
  next,
  back,
}: StepEnvironmentProps) {
  const [openEnvModal, setOpenEnvModal] = useState(false);
  const [saved, setSaved] = useState(false);

  // --------------------------------------------
  // 2. Handle environment creation → mark onboarding step
  // --------------------------------------------
  async function handleEnvSaved() {
    setSaved(true);
    await refreshUser();
    next();
  }

  // --------------------------------------------
  // Render UI
  // --------------------------------------------
  return (
    <StepLayout title="Application & environment" description="Add the application URL and defaults for the environment your team will test first.">
      {!projectId && (
        <p className="repository-error">
          No project found — go back and create one first.
        </p>
      )}

      <button
        className="workspace-button workspace-primary"
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
      <StepFooter onNext={saved ? next : undefined} onBack={back} />
    </StepLayout>
  );
}
