"use client";

import { useFeatures } from "@/components/providers/FeatureFlagsProvider";
import { useState } from "react";
import StepProject from "./steps/StepProject";
import StepEnvironment from "./steps/StepEnvironment";
import StepTestImport from "./steps/StepTestImport";
import StepFinish from "./steps/StepFinish";
import StepTeam from "./steps/StepTeam";
import { WorkspaceDialog } from "@/components/ui/workspace-dialog";
import { User } from "@/types/user";
import { OnboardingStep } from "../onboarding/types";

const STEP_LABELS = ["Project", "Application", "Team", "Optional import", "Ready"];

interface OnboardingModalProps {
  user: User;
  refreshUser: () => Promise<void>;
  onProjectsReload: () => Promise<void>;
  onClose: () => void;
}

export default function OnboardingModal({
  user,
  refreshUser,
  onProjectsReload,
  onClose,
}: OnboardingModalProps) {
  const { enabled } = useFeatures();
  const labels = enabled("customer_accounts") ? ["Account & project", ...STEP_LABELS.slice(1)] : STEP_LABELS;
  const maxStep = 5;

  const [step, setStep] = useState<OnboardingStep>(
    Math.max(1, Math.min(5, user?.onboarding?.current_step || 1)) as OnboardingStep
  );

  const next = () =>
    setStep((prev) => (Math.min(maxStep, prev + 1) as OnboardingStep));

  const back = () =>
    setStep((prev) => (Math.max(1, prev - 1) as OnboardingStep));

  // Get project ID from onboarding context
  const projectId = user?.onboarding?.context?.project_id || null;

  const steps: Record<OnboardingStep, React.ReactNode> = {
    1: (
      <StepProject
        user={user}
        refreshUser={refreshUser}
        next={next}
      />
    ),

    2: (
      <StepEnvironment
        projectId={projectId}
        refreshUser={refreshUser}
        next={next}
        back={back}
      />
    ),

    3: (
      <StepTeam projectId={projectId} next={next} back={back} />
    ),

    4: (
      <StepTestImport
        next={next}
        projectId={projectId}
      />
    ),

    5: (
      <StepFinish
        user={user}
        onProjectsReload={onProjectsReload}
        refreshUser={refreshUser}
        close={onClose}
        back={back}
      />
    ),
  };

  return (
    <WorkspaceDialog open onClose={onClose} title="Set up your QA workspace" className="onboarding-dialog">
      <header className="onboarding-header">
        <p className="workspace-eyebrow">Welcome to AI QA Squad</p>
        <h1>Set up your QA workspace</h1>
        <p>Create a project first. Product knowledge and story-based test design come next.</p>
      </header>
      <ol className="onboarding-stepper" aria-label={`Setup step ${step} of ${maxStep}`}>
        {labels.map((label, index) => <li key={label} aria-current={index + 1 === step ? "step" : undefined}
          className={index + 1 < step ? "is-complete" : index + 1 === step ? "is-active" : ""}>
          <span aria-hidden="true">{index + 1 < step ? "✓" : index + 1}</span><small>{label}</small>
        </li>)}
      </ol>
      <div className="onboarding-content" key={step}>{steps[step]}</div>
      <p className="onboarding-progress">Step {step} of {maxStep} · You can close setup and return later.</p>
    </WorkspaceDialog>
  );
}
