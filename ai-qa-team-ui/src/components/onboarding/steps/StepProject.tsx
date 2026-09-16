"use client";

import { useState } from "react";
import StepFooter from "../StepFooter";
import { apiFetch } from "@/utils/api";
import { User } from "@/types/user";
import StepLayout from "../StepLayout";

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
    const res = await apiFetch("/projects", {
      method: "POST",
      body: JSON.stringify({
        name,
        created_by: user.email,
      }),
    });

    if (res.ok) {
      await refreshUser();
      next();
    }

    setSaving(false);
  }

  return (
    <StepLayout title="Create your project" description="Give your QA workspace a clear name. You can change it later.">
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Project name"
        aria-label="Project name"
      />

      <StepFooter
        onNext={saveProject}
        disabled={saving || name.length < 3}
      />
    </StepLayout>
  );
}
