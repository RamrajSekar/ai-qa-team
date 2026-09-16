"use client";
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
  const canDiscover = enabled("repository_discovery", "test_registry");

  async function finishAutomationStep() {
    await apiFetch("/onboarding/progress", { method: "PUT", body: JSON.stringify({ step_key: "test_import", current_step: 4 }) });
    next();
  }

  // ---------------------------------------------
  // If user reached this step without a project
  // ---------------------------------------------
  if (!ready) return <p role="status">Loading features...</p>;
  if (!canDiscover) return (
    <StepLayout title="Connect your automation" description="Repository discovery is currently unavailable.">
      <button onClick={finishAutomationStep} className="workspace-button workspace-primary">Continue</button>
    </StepLayout>
  );

  if (!projectId) {
    return (
      <StepLayout title="Connect your automation" description="A project must be created before connecting a repository."><button onClick={finishAutomationStep} className="workspace-button">Skip for now</button></StepLayout>
    );
  }

  return (
    <StepLayout title="Connect your automation" description="Connect your existing automation repository so AI QA Team can discover the tests you already have. No test rewrite required.">
      <RepositoryManager projectId={projectId} onboarding onContinue={finishAutomationStep} onSkip={finishAutomationStep} />
    </StepLayout>
  );
}
