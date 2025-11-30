"use client";

import { useEffect } from "react";
import { useAuth } from "@/components/providers/AuthProvider";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { refreshSubscription } = useAuth();

  useEffect(() => {
    refreshSubscription(); // refresh usage & limits
  }, [refreshSubscription]);

  // ❗ No sidebar/topbar here — global layout already includes them
  return <>{children}</>;
}