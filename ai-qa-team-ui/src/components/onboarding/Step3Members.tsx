"use client";

import StepFooter from "./StepFooter";
import StepLayout from "./StepLayout";

export default function Step3Members({ onNext, onBack }: { onNext: () => void; onBack: () => void; }) {
  return (
    <StepLayout
      title="Invite Team Members"
      description="Invite your QA team to collaborate."
    >
      <p className="text-gray-500 mb-4">Team invite UI goes here.</p>

      {/* <StepFooter next={onNext} back={onBack} /> */}
    </StepLayout>
  );
}
