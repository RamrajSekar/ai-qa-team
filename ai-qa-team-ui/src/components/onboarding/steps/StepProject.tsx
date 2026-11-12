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
  const [error, setError] = useState("");

  async function saveProject() {
    if (!name.trim()) return;
    setSaving(true);

    setError("");
    try {
      const res = await apiFetch("/projects", { method: "POST", body: JSON.stringify({ name: name.trim(), created_by: user.email }) });
      if (!res.ok) throw new Error(typeof res.data?.detail === "string" ? res.data.detail : "Could not create project. Please try again.");
      window.dispatchEvent(new Event("projects-updated"));
      await refreshUser();
      next();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not reach the project service.");
    } finally { setSaving(false); }
  }

  return (
    <StepLayout title="Create your project" description="Give your QA workspace a clear name. You can change it later.">
      <label htmlFor="onboarding-project-name">Project name</label>
      <input id="onboarding-project-name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Project name"
        aria-label="Project name"
      />

      {error && <p role="alert" className="repository-error">{error}</p>}
      <StepFooter
        onNext={saveProject}
        nextLabel={saving ? "Creating project…" : "Create project & continue"}
        disabled={saving || name.trim().length < 3}
      />
    </StepLayout>
  );
}
