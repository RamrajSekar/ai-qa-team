"use client";

import { StepContainer } from "@/components/onboarding/StepContainer";
import { StepHeader } from "@/components/onboarding/StepHeader";
import  StepFooter  from "@/components/onboarding/StepFooter";

export default function Step3() {
  return (
    <StepContainer>
      <StepHeader
        title="Add Environments"
        subtitle="You already created environment components, reuse them here."
      />

      {/* You will embed <EnvironmentForm /> here */}

      <StepFooter
        next="/onboarding/step-4"
        back="/onboarding/step-2"
      />
    </StepContainer>
  );
}
