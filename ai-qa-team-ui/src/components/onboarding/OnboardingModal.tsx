"use client";

import { useState } from "react";
import StepProject from "./steps/StepProject";
import StepEnvironment from "./steps/StepEnvironment";
import StepTestImport from "./steps/StepTestImport";
import StepFinish from "./steps/StepFinish";
import StepTeam from "./steps/StepTeam";
import { X } from "lucide-react";
import { User } from "@/types/user";
import { OnboardingStep } from "../onboarding/types";

const STEP_LABELS = ["Project", "Application", "Team", "Automation", "Ready"];

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
  const maxStep = 5;

  const [step, setStep] = useState<OnboardingStep>(
    (user?.onboarding?.current_step as OnboardingStep) || 1
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
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
      <div className="onboarding-dialog relative">

        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-500 hover:text-gray-700"
        >
          <X size={24} />
        </button>

        <div className="onboarding-stepper" aria-label={`Setup step ${step} of ${maxStep}`}>
          {STEP_LABELS.map((label, index) => <div key={label} className={index + 1 <= step ? "is-active" : ""}><span>{index + 1}</span><small>{label}</small></div>)}
        </div>

        {steps[step]}
      </div>
    </div>
  );
}
