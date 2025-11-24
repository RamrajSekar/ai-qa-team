"use client";

import { useAuth } from "@/components/providers/AuthProvider";
import { useState } from "react";
import { ChevronDown } from "lucide-react";

export default function ProfileMenu() {
  const { user, setAuth } = useAuth();
  const [open, setOpen] = useState(false);

  const logout = async () => {
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/logout`, {
      method: "POST",
      credentials: "include",
    });

    setAuth(null);
    window.location.href = "/";
  };

  if (!user) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((p) => !p)}
        className="flex items-center gap-2 px-3 py-1.5 bg-neutral-100 dark:bg-neutral-800 rounded-full"
      >
        <div className="w-7 h-7 bg-neutral-300 rounded-full flex items-center justify-center">
          {user.name?.[0] ?? "?"}
        </div>

        <div className="flex flex-col items-start text-xs leading-tight">
          <span className="font-semibold">{user.name}</span>
          <span className="text-neutral-500">{user.subscription?.plan}</span>
        </div>

        <ChevronDown size={14} />
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-40 bg-white dark:bg-neutral-900 shadow-xl border border-neutral-200 dark:border-neutral-700 rounded-md p-2 text-sm">
          <button
            onClick={logout}
            className="w-full text-left px-3 py-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded"
          >
            Logout
          </button>
        </div>
      )}
    </div>
  );
}
