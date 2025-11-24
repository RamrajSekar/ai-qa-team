"use client";
export const dynamic = "force-dynamic";
export const fetchCache = "force-no-store";


import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/providers/AuthProvider";

export default function OAuthCallbackPage() {
  console.log("STEP A: OAuth callback loaded");

  const router = useRouter();
  const { setAuth } = useAuth();

  useEffect(() => {
    async function handleOAuthCallback() {
      console.log("STEP B: handleOAuthCallback triggered");

      if (typeof window === "undefined") {
        console.log("STEP B1: window undefined → this should never run on server");
        return;
      }

      const query = new URLSearchParams(window.location.search);
      const raw = query.get("data");

      if (!raw) {
        console.error("STEP C: Missing data payload");
        router.push("/");
        return;
      }

      let payload;
      try {
        payload = JSON.parse(raw);
      } catch (err) {
        console.error("STEP D: Failed to parse payload", err);
        router.push("/");
        return;
      }

      const { user } = payload;

      console.log("STEP E: Parsed user:", user);

      setAuth(user);

      console.log("STEP F: Redirecting to /dashboard");

      // Allow browser to flush cookies that backend set
      setTimeout(() => router.push("/dashboard"), 100);
    }

    handleOAuthCallback();
  }, [router, setAuth]);

  return (
    <div className="flex h-screen items-center justify-center text-lg">
      Authenticating...
    </div>
  );
}
