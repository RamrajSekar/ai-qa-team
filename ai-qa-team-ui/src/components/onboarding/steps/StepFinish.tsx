"use client";
import { useState } from "react";
import { apiFetch } from "@/utils/api";

interface StepFinishProps {
  user: any;
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
    <div className="p-6 text-center">
      <h2 className="text-2xl font-bold mb-3">You're All Set! 🎉</h2>

      <p className="text-gray-600 mb-6">
        Your first project and environment are ready.  
        You can manage them from your dashboard.
      </p>

      <div className="flex justify-center gap-3">
        <button
          onClick={back}
          className="px-4 py-2 rounded-md bg-gray-200 hover:bg-gray-300"
        >
          Back
        </button>

        <button
          className="bg-purple-600 text-white px-6 py-2 rounded-md hover:bg-purple-700"
          onClick={complete}
        >
          Go to Dashboard
        </button>
      </div>
    </div>
  );
}
