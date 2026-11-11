"use client";

import { useAuth } from "@/components/providers/AuthProvider";

export default function PlatformAdminGuard({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user) return <p className="workspace-description">Loading platform access…</p>;
  if (user.platform_role !== "OWNER" && user.platform_role !== "ADMIN") {
    return <div className="workspace-empty"><strong>Platform administration unavailable</strong><p>This area requires a platform OWNER or ADMIN role.</p></div>;
  }
  return children;
}
