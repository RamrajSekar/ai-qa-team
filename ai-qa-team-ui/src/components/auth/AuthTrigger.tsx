"use client";

import { ReactNode } from "react";
import { useAuth } from "../providers/AuthProvider";

export default function AuthTrigger({ children }: { children: ReactNode }) {
  const { openAuth } = useAuth();

  return (
    <button onClick={openAuth} className="px-4 py-2 rounded-xl bg-indigo-600 text-white font-medium">
      {children}
    </button>
  );
}
