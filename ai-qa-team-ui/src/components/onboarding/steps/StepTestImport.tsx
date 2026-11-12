"use client";
import { useState } from "react";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";
import RepositoryManager from "@/components/repositories/RepositoryManager";
import { apiFetch } from "@/utils/api";
import StepLayout from "../StepLayout";

interface StepTestImportProps {
  next: () => void;
  projectId: string | null;
}

export default function StepTestImport({ next, projectId }: StepTestImportProps) {
  const { enabled, ready } = useFeatures();
  const canDiscover = enabled("repository_discovery", "test_registry", "repository_ui");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function finishAutomationStep() {
    setBusy(true); setError("");
    try {
      const result = await apiFetch("/onboarding/progress", { method: "PUT", body: JSON.stringify({ step_key: "test_import", current_step: 5 }) });
      if (!result.ok) throw new Error("Could not save progress. Try again.");
      next();
    } catch { setError("Could not save progress. Try again."); }
    finally { setBusy(false); }
  }

  // ---------------------------------------------
  // If user reached this step without a project
  // ---------------------------------------------
  if (!ready) return <p role="status">Loading features...</p>;
  if (!canDiscover) return (
    <StepLayout title="Start with product knowledge" description="An automation repository is optional. After setup, open Product Knowledge to teach your application context, then add a story and acceptance criteria.">
      {error && <p role="alert">{error}</p>}<button disabled={busy} onClick={finishAutomationStep} className="workspace-button workspace-primary">{busy ? "Saving…" : "Continue"}</button>
    </StepLayout>
  );

  if (!projectId) {
    return (
      <StepLayout title="Connect your automation" description="A project must be created before connecting a repository."><button onClick={finishAutomationStep} className="workspace-button">Skip for now</button></StepLayout>
    );
  }

  return (
    <StepLayout title="Connect your automation" description="Optional: connect an existing automation repository. You can skip this and begin with product knowledge and stories.">
      {error && <p role="alert">{error}</p>}
      <RepositoryManager projectId={projectId} onboarding onContinue={finishAutomationStep} onSkip={finishAutomationStep} />
    </StepLayout>
  );
}
