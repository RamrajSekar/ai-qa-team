"use client";

import { useState } from "react";
import StepProject from "./steps/StepProject";
import StepEnvironment from "./steps/StepEnvironment";
import StepTestImport from "./steps/StepTestImport";
import StepFinish from "./steps/StepFinish";
import { X } from "lucide-react";
import { User } from "@/types/user";
import { OnboardingStep } from "../onboarding/types";

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
  const maxStep = 4;

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
        user={user}
        refreshUser={refreshUser}
        next={next}
        back={back}
      />
    ),

    3: (
      <StepTestImport
        next={next}
        projectId={projectId}
      />
    ),

    4: (
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
      <div className="bg-white w-full max-w-2xl rounded-lg p-6 shadow-xl relative">

        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-500 hover:text-gray-700"
        >
          <X size={24} />
        </button>

        {/* Progress Bar */}
        <div className="h-2 w-full bg-gray-200 rounded mb-6">
          <div
            className="h-full bg-purple-600 rounded transition-all"
            style={{ width: `${(step / maxStep) * 100}%` }}
          />
        </div>

        {steps[step]}
      </div>
    </div>
  );
}
