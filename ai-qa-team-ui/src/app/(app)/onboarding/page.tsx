"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/providers/AuthProvider";
import OnboardingModal from "@/components/onboarding/OnboardingModal";

export default function OnboardingPage() {
  const router = useRouter();
  const { user, refreshSubscription } = useAuth();
  const completed = user?.onboarding?.onboarding_status === "completed";
  useEffect(() => { if (completed) router.replace("/dashboard"); }, [completed, router]);
  // AuthProvider owns session loading. Refreshing on each user-object change loops.
  if (!user || completed) return <p role="status">Loading workspace setup…</p>;
  return <OnboardingModal user={user} refreshUser={refreshSubscription}
    onProjectsReload={async () => { window.dispatchEvent(new Event("projects-updated")); }}
    onClose={() => router.push("/projects")} />;
}
