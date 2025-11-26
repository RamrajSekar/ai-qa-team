"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/providers/AuthProvider";

export default function AuthPageInner() {
  const router = useRouter();
  const params = useSearchParams();
  const plan = params.get("plan") ?? "free";

  const { user, openAuth } = useAuth();

  useEffect(() => {
    // Logged in? → redirect to dashboard
    if (user) {
      router.replace("/dashboard");
      return;
    }

    // Not logged in → open modal
    openAuth();
  }, [user, router, openAuth]);

  return null;
}
