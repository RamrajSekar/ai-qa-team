"use client";

export function StepContainer({ children }: { children: React.ReactNode }) {
  return (
    <div className="max-w-xl mx-auto py-12 px-6">
      {children}
    </div>
  );
}
