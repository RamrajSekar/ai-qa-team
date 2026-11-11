"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/providers/AuthProvider";
import OnboardingModal from "@/components/onboarding/OnboardingModal";

export default function OnboardingPage() {
  const router = useRouter();
  const { user, setUser } = useAuth();

  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);

  async function refreshUser() {
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/auth/me`,
        { credentials: "include" }
      );
      if (res.ok) {
        const data = await res.json();
        setUser(data.user);
      }
    } catch (err) {
      console.error("Failed to refresh user", err);
    }
  }

  async function reloadProjects() {
    // No-op here. The Dashboard handles real project reload.
    return Promise.resolve();
  }

  useEffect(() => {
    async function init() {
      if (!user) {
        setLoading(false);
        return;
      }

      await refreshUser();

      if (user.onboarding?.onboarding_status !== "completed") {
        setOpen(true);
      } else {
        router.push("/dashboard");
        return;
      }

      setLoading(false);
    }

    init();
  }, [user]);

  if (!user) return <p className="p-6">Loading...</p>;
  if (loading) return <p className="p-6">Loading onboarding...</p>;

  return (
    <div className="p-10">
      {open && (
        <OnboardingModal
          user={user}
          refreshUser={refreshUser}
          onProjectsReload={reloadProjects}
          onClose={() => {
            setOpen(false);
            router.push("/dashboard");
          }}
        />
      )}
    </div>
  );
}
