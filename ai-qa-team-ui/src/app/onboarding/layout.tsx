// "use client";

import StepGuard from "./StepGuard";

export default function OnboardingLayout({ children }: { children: React.ReactNode }) {
  return <StepGuard>{children}</StepGuard>;
}
