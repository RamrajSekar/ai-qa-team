"use client";
export const dynamic = "force-dynamic";
export const fetchCache = "force-no-store";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/providers/AuthProvider";

const API_URL = process.env.NEXT_PUBLIC_API_URL as string;

export default function OAuthCallbackPage() {
  const router = useRouter();
  const { setUser, pendingPlan, setPendingPlan } = useAuth();

  useEffect(() => {
    async function handleOAuthCallback() {
      console.log("STEP A: Callback started");

      if (typeof window === "undefined") {
        console.warn("STEP A1: Callback executed during SSR — skipped");
        return;
      }

      const query = new URLSearchParams(window.location.search);
      const raw = query.get("data");

      if (!raw) {
        console.error("STEP B: Missing ?data payload");
        router.push("/");
        return;
      }

      let payload;
      try {
        payload = JSON.parse(raw);
      } catch (err) {
        console.error("STEP C: Invalid JSON payload", err);
        router.push("/");
        return;
      }

      const { user } = payload;

      if (!user) {
        console.error("STEP D: No user found in payload");
        router.push("/");
        return;
      }

      console.log("STEP E: Parsed user:", user);

      // Update global auth state
      setUser(user);

      // -----------------------------------------------------
      // AUTO-UPGRADE PLAN AFTER OAUTH SIGNUP/LOGIN
      // -----------------------------------------------------
      if (pendingPlan) {
        console.log("STEP F: Applying pending plan:", pendingPlan);

        try {
          await fetch(`${API_URL}/auth/upgrade-plan?plan=${pendingPlan}`, {
            method: "PATCH",
            credentials: "include",
          });
        } catch (err) {
          console.error("STEP F1: Failed to auto-upgrade plan", err);
        }

        // Clear after applying
        setPendingPlan(null);
      }

      console.log("STEP G: Redirecting to /dashboard");

      // Allow browser to flush HttpOnly cookies
      setTimeout(() => router.push("/dashboard"), 120);
    }

    handleOAuthCallback();
  }, [router, setUser, pendingPlan, setPendingPlan]);

  return (
    <div className="flex h-screen items-center justify-center text-lg">
      Authenticating...
    </div>
  );
}
