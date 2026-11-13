"use client";

import { useState } from "react";
import StepFooter from "../StepFooter";
import EnvironmentModal from "@/components/environment/EnvironmentModal";
import StepLayout from "../StepLayout";
import { apiFetch } from "@/utils/api";

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
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function skip() {
    setBusy(true); setError("");
    try {
      const result = await apiFetch("/onboarding/progress", { method: "PUT", body: JSON.stringify({ current_step: 3 }) });
      if (!result.ok) throw new Error("Could not save setup progress.");
      await refreshUser(); next();
    } catch { setError("Could not save setup progress. Please try again."); }
    finally { setBusy(false); }
  }

  // --------------------------------------------
  // 2. Handle environment creation → mark onboarding step
  // --------------------------------------------
  async function handleEnvSaved() {
    await refreshUser();
    next();
  }

  // --------------------------------------------
  // Render UI
  // --------------------------------------------
  return (
    <StepLayout title="Application & environment (optional)" description="You can add this later under Environments. Add the application URL and defaults. Use the Credentials tab to add an application role, username and password. Passwords are encrypted when saved.">
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
      {error && <p role="alert">{error}</p>}
      <StepFooter onNext={skip} nextLabel={busy ? "Saving…" : "Skip for now"} disabled={busy} onBack={busy ? undefined : back} />
    </StepLayout>
  );
}
