"use client";

import { useFeatures } from "@/components/providers/FeatureFlagsProvider";
import { useState } from "react";
import StepProject from "./steps/StepProject";
import StepEnvironment from "./steps/StepEnvironment";
import StepFinish from "./steps/StepFinish";
import StepTeam from "./steps/StepTeam";
import StepAI from "./steps/StepAI";
import { WorkspaceDialog } from "@/components/ui/workspace-dialog";
import { User } from "@/types/user";
import { OnboardingStep } from "../onboarding/types";

// Preserve persisted step numbers; removed import step resumes at AI Setup.
const STEP_IDS: OnboardingStep[] = [1, 2, 3, 5, 6];
const STEP_LABELS = ["Project", "Application (optional)", "Team", "AI Setup", "Ready"];

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
  const maxStep = STEP_IDS.length;

  const [step, setStep] = useState<OnboardingStep>(
    (user?.onboarding?.current_step === 4 ? 5 : Math.max(1, Math.min(6, user?.onboarding?.current_step || 1))) as OnboardingStep
  );

  const next = () =>
    setStep((prev) => STEP_IDS[Math.min(STEP_IDS.length - 1, STEP_IDS.indexOf(prev) + 1)]);

  const back = () =>
    setStep((prev) => STEP_IDS[Math.max(0, STEP_IDS.indexOf(prev) - 1)]);

  // Get project ID from onboarding context
  const projectId = user?.onboarding?.context?.project_id || null;

  const position = STEP_IDS.indexOf(step) + 1;
  const steps: Partial<Record<OnboardingStep, React.ReactNode>> = {
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

    5: (
      <StepAI projectId={projectId} next={next} back={back} />
    ),

    6: (
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
      <ol className="onboarding-stepper" aria-label={`Setup step ${position} of ${maxStep}`}>
        {labels.map((label, index) => <li key={label} aria-current={index + 1 === position ? "step" : undefined}
          className={index + 1 < position ? "is-complete" : index + 1 === position ? "is-active" : ""}>
          <span aria-hidden="true">{index + 1 < position ? "✓" : index + 1}</span><small>{label}</small>
        </li>)}
      </ol>
      <div className="onboarding-content" key={step}>{steps[step]}</div>
      <p className="onboarding-progress">Step {position} of {maxStep} · You can close setup and return later.</p>
    </WorkspaceDialog>
  );
}
