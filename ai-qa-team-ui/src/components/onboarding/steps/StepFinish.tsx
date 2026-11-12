"use client";
import { useState } from "react";
import { apiFetch } from "@/utils/api";
import type { User } from "@/types/user";

interface StepFinishProps {
  user: User;
  refreshUser: () => Promise<void>;
  onProjectsReload: () => Promise<void>;
  close: () => void;
  back: () => void;
}

export default function StepFinish({
  user,
  refreshUser,
  onProjectsReload,
  close,
  back,
}: StepFinishProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  async function complete() {
    setSaving(true); setError("");
    try {
      const response = await apiFetch("/onboarding/finish", { method: "POST", body: JSON.stringify({ name: "", created_by: user.email }) });
      if (!response.ok) throw new Error("Setup could not be saved. Please try again.");
      await refreshUser(); await onProjectsReload(); close();
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Could not save setup."); }
    finally { setSaving(false); }
  }

  return (
    <div className="onboarding-finish">
      <h2>Project ready</h2>

      <p className="text-gray-600 mb-6">
        Your workspace is ready. Add product knowledge, review a story and generate test designs from the project workspace.
      </p>

      {error && <p role="alert" className="repository-error">{error}</p>}
      <div className="flex justify-center gap-3">
        <button
          onClick={back}
          className="workspace-button"
        >
          Back
        </button>

        <button
          className="workspace-button workspace-primary"
          disabled={saving}
          onClick={complete}
        >
          {saving ? "Saving setup…" : "Open workspace"}
        </button>
      </div>
    </div>
  );
}
