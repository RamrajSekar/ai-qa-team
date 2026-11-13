"use client";

import { useEffect, useState } from "react";
import StepFooter from "../StepFooter";
import { apiFetch } from "@/utils/api";
import { User } from "@/types/user";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";
import StepLayout from "../StepLayout";

interface StepProjectProps {
  user: User;
  refreshUser: () => Promise<void>;
  next: () => void;
}

export default function StepProject({ user, refreshUser, next }: StepProjectProps) {
  const { enabled } = useFeatures();
  const accounts = enabled("customer_accounts");
  const canManage = user.account_role === "OWNER" || user.account_role === "ADMIN";
  const [accountName, setAccountName] = useState("");
  const [accountLoaded, setAccountLoaded] = useState(false);
  const [name, setName] = useState("");
  const existingProject = user.onboarding?.context?.project_id;
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!accounts) return;
    const controller = new AbortController();
    apiFetch("/account", { signal: controller.signal }).then(result => {
      if (!result.ok) throw new Error("Could not load the customer account.");
      if (!controller.signal.aborted) { setAccountName(result.data.name || ""); setAccountLoaded(true); }
    }).catch(() => { if (!controller.signal.aborted) setError("Could not load the customer account. Reopen setup to try again."); });
    return () => controller.abort();
  }, [accounts]);

  async function saveProject() {
    if (existingProject) { next(); return; }
    if (!name.trim()) return;
    setSaving(true);

    setError("");
    try {
      if (accounts) {
        if (!canManage) throw new Error("Ask an account administrator to create the project.");
        const account = await apiFetch("/account", { method: "PATCH", body: JSON.stringify({ name: accountName.trim() }) });
        if (!account.ok) throw new Error("Could not save the customer account name.");
      }
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
    <StepLayout title={accounts ? "Name your account & first project" : "Create your project"} description={accounts ? "Your customer account groups your team and projects. Give your first project a clear name." : "Give your first project a clear name."}>
      {accounts && !existingProject && <><label htmlFor="onboarding-account-name">Customer / account name</label><input id="onboarding-account-name" value={accountName} maxLength={160} disabled={!canManage || !accountLoaded} onChange={event => setAccountName(event.target.value)} placeholder="Customer or company name" />{!canManage && <p>Only an account owner or administrator can edit account details and create projects.</p>}</>}
      {existingProject ? <p>Your project is already created. Continue setup without creating another project.</p> : <>
      <label htmlFor="onboarding-project-name">Project name</label>
      <input id="onboarding-project-name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Project name"
        aria-label="Project name"
      />
      </>}

      {error && <p role="alert" className="repository-error">{error}</p>}
      <StepFooter
        onNext={saveProject}
        nextLabel={existingProject ? "Continue" : saving ? "Creating project…" : "Create project & continue"}
        disabled={saving || (!existingProject && (name.trim().length < 3 || (accounts && (!accountLoaded || !canManage || accountName.trim().length < 2))))}
      />
    </StepLayout>
  );
}
