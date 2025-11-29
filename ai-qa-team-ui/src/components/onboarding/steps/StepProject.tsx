"use client";

import { useState } from "react";
import StepFooter from "../StepFooter";
import { apiFetch } from "@/utils/api";
import { User } from "@/types/user";

interface StepProjectProps {
  user: User;
  refreshUser: () => Promise<void>;
  next: () => void;
}

export default function StepProject({ user, refreshUser, next }: StepProjectProps) {
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);

  async function saveProject() {
    if (!name.trim()) return;
    setSaving(true);

    // Create project
    const res = await apiFetch(`${process.env.NEXT_PUBLIC_API_URL}/projects`, {
      method: "POST",
      body: JSON.stringify({
        name,
        created_by: user.email,
      }),
    });

    if (res.ok) {
      // Update onboarding step
      await apiFetch(`${process.env.NEXT_PUBLIC_API_URL}/onboarding/progress`, {
        method: "PUT",
        body: JSON.stringify({
          step_key: "project",
          current_step: 2,
        }),
      });

      await refreshUser();
      next();
    }

    setSaving(false);
  }

  return (
    <div className="p-6">
      <h2 className="font-bold text-xl mb-4">Create Your First Project</h2>

      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Project Name"
        className="w-full border rounded-md p-3"
      />

      <StepFooter
        onNext={saveProject}
        disabled={saving || name.length < 3}
      />
    </div>
  );
}
