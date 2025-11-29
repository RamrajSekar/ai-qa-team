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
    <div className="flex justify-between mt-8">
      {onBack ? (
        <button
          onClick={onBack}
          className="px-4 py-2 rounded-md border hover:bg-gray-100"
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
          className={`px-4 py-2 rounded-md bg-purple-600 text-white 
            hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed`}
        >
          {nextLabel}
        </button>
      )}
    </div>
  );
}
