"use client";

import { useAuth } from "@/components/providers/AuthProvider";

export default function AuthTrigger({ children }: { children: React.ReactNode }) {
  const { openAuth } = useAuth();

  return (
    <button
      onClick={() => openAuth()}
      className="px-4 py-2 rounded-xl bg-indigo-600 text-white font-medium hover:bg-indigo-700 transition"
    >
      {children}
    </button>
  );
}
