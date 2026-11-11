// src/app/(app)/layout.tsx
"use client";

import { FeatureFlagsProvider, FeatureRouteGuard } from "@/components/providers/FeatureFlagsProvider";
import ThemeProvider from "@/components/ThemeProvider";
import Sidebar from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { ProjectsProvider } from "@/hooks/useProjects";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <FeatureFlagsProvider>
        <ProjectsProvider>
          <div className="workspace-shell">
            <Sidebar />
            <div className="workspace-body">
              <Topbar />
              <main className="workspace-main"><FeatureRouteGuard>{children}</FeatureRouteGuard></main>
            </div>
          </div>
        </ProjectsProvider>
      </FeatureFlagsProvider>
    </ThemeProvider>
  );
}
