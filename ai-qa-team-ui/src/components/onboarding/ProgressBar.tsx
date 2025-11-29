"use client";

export function ProgressBar({ step }: { step: number }) {
  const total = 6;
  const percentage = (step / total) * 100;

  return (
    <div className="w-full h-2 bg-gray-200 rounded mt-6 mb-10">
      <div
        className="h-full bg-indigo-600 rounded transition-all"
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
}
