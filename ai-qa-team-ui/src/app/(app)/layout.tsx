// "use client";

// import "..app/globals/css";
// import {AuthProvider} from "@/components/providers/AuthProvider";
// import AuthModal from "@/components/auth/AuthModal";
"use client";

import "../globals.css";
import Sidebar from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { AuthProvider } from "@/components/providers/AuthProvider";

const metadata = {
  title: "QA Squad",
  description: "AI-powered test automation companion",
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <div className="flex w-full h-full">
        <Sidebar />

        <div className="flex-1 flex flex-col">
          <Topbar />
          <main className="p-6">{children}</main>
        </div>
      </div>
    </AuthProvider>
  );
}

