"use client";

import { useState } from "react";
import StepProject from "./steps/StepProject";
import StepEnvironment from "./steps/StepEnvironment";
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

export default function OnboardingModal({ user, refreshUser,onProjectsReload, onClose }:OnboardingModalProps) {
  const [step, setStep] = useState<OnboardingStep>(
    (user?.onboarding?.current_step as OnboardingStep) || 1
  );

  const next = () => setStep((prev) => (Math.min(3, prev + 1) as OnboardingStep));
  const back = () => setStep((prev) => (Math.max(1, prev - 1) as OnboardingStep));

  
  /** FIX: Use React.ReactNode instead of JSX.Element */
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
      <StepFinish
        user={user}
        onProjectsReload={onProjectsReload}
        refreshUser={refreshUser}
        close={onClose}
        back={back}
      />
    )
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
      <div className="bg-white w-full max-w-2xl rounded-lg p-6 shadow-xl">
       {/* ⭐ TOP-RIGHT CLOSE BUTTON ⭐ */}
        <button
          onClick={onClose}
          className="
            absolute 
            top-4 right-4 
            text-gray-500 hover:text-gray-700
            transition
          "
        >
          <X size={24} />
        </button>
        {/* Progress bar */}
        <div className="h-2 w-full bg-gray-200 rounded mb-4">
          <div
            className="h-full bg-purple-600 rounded"
            style={{ width: `${(step / 3) * 100}%` }}
          ></div>
        </div>

        {steps[step]}
      </div>
    </div>
  );
}
