"use client";

import { apiFetch } from "@/utils/api";

interface StepFinishProps {
  refreshUser: () => Promise<void>;
  close: () => void;
}

export default function StepFinish({ refreshUser, close }: StepFinishProps) {
  async function complete() {
    await apiFetch(`${process.env.NEXT_PUBLIC_API_URL}/onboarding/finish`, {
      method: "POST",
    });

    await refreshUser();
    close();
  }

  return (
    <div className="p-6 text-center">
      <h2 className="text-2xl font-bold mb-3">You're All Set! 🚀</h2>
      <p className="text-gray-600 mb-6">
        Your first project and environment are ready.  
        You can now begin creating scenarios and automated tests.
      </p>

      <button
        className="bg-purple-600 text-white px-6 py-2 rounded-md hover:bg-purple-700"
        onClick={complete}
      >
        Go to Dashboard
      </button>
    </div>
  );
}
