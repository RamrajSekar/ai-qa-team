"use client";

import { StepContainer } from "@/components/onboarding/StepContainer";
import { StepHeader } from "@/components/onboarding/StepHeader";

export default function Step6() {
  return (
    <StepContainer>
      <StepHeader
        title="You're all set!"
        subtitle="Redirecting you to your dashboard..."
      />

      <p>Your workspace is ready.</p>

      <meta httpEquiv="refresh" content="1; URL=/dashboard" />
    </StepContainer>
  );
}
