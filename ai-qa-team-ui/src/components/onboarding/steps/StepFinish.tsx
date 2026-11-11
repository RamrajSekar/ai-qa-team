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
  const [name] = useState("");
  async function complete() {
    await apiFetch("/onboarding/finish", {
      method: "POST",
      body: JSON.stringify({
        name,
        created_by: user.email,
      })});

    await refreshUser();
    await onProjectsReload(); // refresh dashboard project list

    close(); // close onboarding modal
  }

  return (
    <div className="onboarding-finish">
      <h2>Project ready</h2>

      <p className="text-gray-600 mb-6">
        Your project setup is saved. You can manage environments and repositories from the project workspace.
      </p>

      <div className="flex justify-center gap-3">
        <button
          onClick={back}
          className="workspace-button"
        >
          Back
        </button>

        <button
          className="workspace-button workspace-primary"
          onClick={complete}
        >
          Go to Dashboard
        </button>
      </div>
    </div>
  );
}
