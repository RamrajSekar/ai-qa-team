// src/app/(app)/layout.tsx
"use client";

import { AuthProvider } from "@/components/providers/AuthProvider";
import { FeatureFlagsProvider, FeatureRouteGuard } from "@/components/providers/FeatureFlagsProvider";
import ThemeProvider from "@/components/ThemeProvider";
import Sidebar from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <ThemeProvider>
      <FeatureFlagsProvider>
      <div className="workspace-shell">
        <Sidebar />
        <div className="workspace-body">
          <Topbar />
          <main className="workspace-main"><FeatureRouteGuard>{children}</FeatureRouteGuard></main>
        </div>
      </div>
      </FeatureFlagsProvider>
      </ThemeProvider>
    </AuthProvider>
  );
}
