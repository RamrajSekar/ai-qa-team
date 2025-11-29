"use client";

import StepFooter from "./StepFooter";
import StepLayout from "./StepLayout";

export default function Step6Finish({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  return (
    <StepLayout
      title="You're Ready!"
      description="Your QA workspace is fully configured. Let's begin!"
    >
      <p className="text-gray-500 mb-6">Click Finish to enter your dashboard.</p>

      {/* <StepFooter
        onNext={onNext}
        onBack={onBack}
        isLast
      /> */}
    </StepLayout>
  );
}
