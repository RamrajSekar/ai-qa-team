"use client";

import { useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useAuth } from "@/components/providers/AuthProvider";

export default function OAuthCallbackInner() {
  const params = useSearchParams();
  const router = useRouter();
  const { setUser } = useAuth();

  useEffect(() => {
    async function processOAuth() {
      try {
        const raw = params.get("data");
        if (!raw) {
          console.error("OAuth callback missing data param");
          router.replace("/auth?error=missing_data");
          return;
        }

        const parsed = JSON.parse(raw);

        // Extract user + tokens
        const { user, access_token, refresh_token } = parsed;

        // Store tokens into cookies (client-side)
        document.cookie = `access_token=${access_token}; path=/`;
        document.cookie = `refresh_token=${refresh_token}; path=/`;

        setUser(user);

        router.replace("/dashboard");
      } catch (err) {
        console.error("OAuth callback error", err);
        router.replace("/auth?error=oauth_failed");
      }
    }

    processOAuth();
  }, [params, router, setUser]);

  return <div className="p-6">Finishing OAuth login…</div>;
}
