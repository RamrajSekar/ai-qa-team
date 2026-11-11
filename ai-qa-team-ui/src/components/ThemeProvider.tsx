"use client";

import { useEffect } from "react";
import { ThemeProvider as NextThemesProvider } from "next-themes";

// Workspace appearance has a separate preference from the landing page toggle.
export default function ThemeProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => () => {
    document.documentElement.removeAttribute("data-workspace-theme");
  }, []);

  return (
    <NextThemesProvider attribute="data-workspace-theme" storageKey="qa-workspace-appearance"
      defaultTheme="system" enableSystem enableColorScheme={false} disableTransitionOnChange>
      {children}
    </NextThemesProvider>
  );
}
