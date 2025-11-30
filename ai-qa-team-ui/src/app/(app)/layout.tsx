// src/app/(app)/layout.tsx
"use client";

import { AuthProvider } from "@/components/providers/AuthProvider";
import Sidebar from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <div className="flex min-h-screen bg-gradient-to-br from-[#f0e9ff] to-[#e8e9ff]">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <Topbar />
          <main className="p-6">{children}</main>
        </div>
      </div>
    </AuthProvider>
  );
}
