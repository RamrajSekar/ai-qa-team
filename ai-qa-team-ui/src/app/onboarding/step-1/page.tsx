"use client";

import { StepContainer } from "@/components/onboarding/StepContainer";
import { StepHeader } from "@/components/onboarding/StepHeader";
import StepFooter from "@/components/onboarding/StepFooter";

export default function Step1() {
  return (
    <StepContainer>
      <StepHeader
        title="Welcome to QA Squad!"
        subtitle="Let’s set up your workspace in a few quick steps."
      />

      <StepFooter next="/onboarding/step-2" />
    </StepContainer>
  );
}
