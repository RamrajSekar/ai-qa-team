"use client";

import { StepContainer } from "@/components/onboarding/StepContainer";
import { StepHeader } from "@/components/onboarding/StepHeader";
import StepFooter from "@/components/onboarding/StepFooter";

export default function Step5() {
  return (
    <StepContainer>
      <StepHeader
        title="Configure AI Assistant"
        subtitle="Set the behavior of your AI test generator."
      />

      {/* AI form here */}

      <StepFooter
        next="/onboarding/step-6"
        back="/onboarding/step-4"
      />
    </StepContainer>
  );
}
