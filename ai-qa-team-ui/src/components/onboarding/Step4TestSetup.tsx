"use client";

import StepFooter from "./StepFooter";
import StepLayout from "./StepLayout";

export default function Step4TestSetup({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  return (
    <StepLayout
      title="Setup Test Execution"
      description="Configure execution environment and test runner."
    >
      <p className="text-gray-500 mb-4">Execution settings coming soon.</p>

      {/* <StepFooter onNext={onNext} onBack={onBack} /> */}
    </StepLayout>
  );
}
