"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/providers/AuthProvider";

export default function AuthPageInner() {
  const router = useRouter();
  const params = useSearchParams();

  // login or signup
  const desiredMode = (params.get("mode") as "login" | "signup") || "login";

  const { user, openAuth, switchMode } = useAuth();

  useEffect(() => {
    // Already logged in → redirect to dashboard
    if (user) {
      router.replace("/dashboard");
      return;
    }

    // Set the auth modal to the correct mode
    switchMode(desiredMode);

    // Open modal (no args)
    openAuth();
  }, [user, router, openAuth, switchMode, desiredMode]);

  return null; // No UI, modal opens globally
}
