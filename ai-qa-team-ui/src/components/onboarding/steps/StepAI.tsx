"use client";

import { useState } from "react";
import Link from "next/link";
import AIConfigurationManager from "@/components/ai/AIConfigurationManager";
import { apiFetch } from "@/utils/api";
import StepLayout from "../StepLayout";

export default function StepAI({ projectId, next, back }: { projectId: string | null; next: () => void; back: () => void }) {
  const [busy, setBusy] = useState(false);
  const [providerBusy, setProviderBusy] = useState(false);
  const [error, setError] = useState("");
  async function continueSetup() {
    setBusy(true); setError("");
    try {
      const response = await apiFetch("/onboarding/progress", { method: "PUT", body: JSON.stringify({ current_step: 6 }) });
      if (!response.ok) throw new Error("Could not save setup progress. Try again.");
      next();
    } catch { setError("Could not save setup progress. Try again."); }
    finally { setBusy(false); }
  }
  return <StepLayout title="AI Setup" description="Managed is selected by default with no customer key. Choose BYOK only if you want to use your provider key. Setup is optional; saving a provider is separate from continuing.">
    {projectId ? <AIConfigurationManager projectId={projectId} onBusyChange={setProviderBusy} /> : <p>Create a project first, or configure AI later.</p>}
    <p>You can return to <Link href="/settings/ai">Workspace → AI Configuration</Link> at any time. Skipping keeps your saved provider, or the Managed default for new setup. It does not save changes or test a connection.</p>
    {error && <p role="alert">{error}</p>}
    <div className="workspace-actions">
      <button className="workspace-button" disabled={busy || providerBusy} onClick={back}>Back</button>
      <button className="workspace-button" disabled={busy || providerBusy} onClick={() => void continueSetup()}>Skip for now</button>
      <button className="workspace-button workspace-primary" disabled={busy || providerBusy} onClick={() => void continueSetup()}>{busy ? "Saving…" : "Continue"}</button>
    </div>
  </StepLayout>;
}
