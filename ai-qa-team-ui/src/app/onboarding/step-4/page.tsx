"use client";

import { StepContainer } from "@/components/onboarding/StepContainer";
import { StepHeader } from "@/components/onboarding/StepHeader";
import StepFooter from "@/components/onboarding/StepFooter";

export default function Step4() {
  return (
    <StepContainer>
      <StepHeader
        title="Invite your team"
        subtitle="Add collaborators to your QA workspace."
      />

      <input
        type="email"
        placeholder="Email"
        className="w-full px-3 py-2 border rounded-md"
      />

      <StepFooter
        next="/onboarding/step-5"
        back="/onboarding/step-3"
      />
    </StepContainer>
  );
}
