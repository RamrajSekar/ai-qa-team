"use client";
import React from "react";

interface StepFooterProps {
  onNext?: () => void;
  onBack?: () => void;
  nextLabel?: string;
  backLabel?: string;
  disabled?: boolean;
}

export default function StepFooter({
  onNext,
  onBack,
  nextLabel = "Continue",
  backLabel = "Back",
  disabled = false,
}: StepFooterProps) {
  return (
    <div className="onboarding-footer">
      {onBack ? (
        <button
          onClick={onBack}
          className="workspace-button"
        >
          {backLabel}
        </button>
      ) : (
        <div />
      )}

      {onNext && (
        <button
          onClick={onNext}
          disabled={disabled}
          className="workspace-button workspace-primary"
        >
          {nextLabel}
        </button>
      )}
    </div>
  );
}
