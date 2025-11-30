"use client";

import { motion } from "framer-motion";
import { useAuth } from "@/components/providers/AuthProvider";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { LogOut, Settings, User2 } from "lucide-react";

export function Topbar() {
  const { user, setUser } = useAuth();
  const plan = user?.subscription?.plan ?? "free";

  const logout = async () => {
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
    setUser(null);
    window.location.href = "/";
  };

  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.35 }}
      className="backdrop-blur-xl bg-white/40 border-b border-white/30 shadow-sm sticky top-0 z-50"
    >
      <div className="flex items-center justify-between px-6 py-4">
        {/* ---- LEFT: TITLE ---- */}
        <h1 className="text-lg font-semibold text-neutral-900">
          AI QA Team
        </h1>

        <div className="flex items-center gap-4">
          {/* ---- PLAN TAG ---- */}
          <span className="
            px-3 py-1 rounded-full 
            text-xs font-semibold 
            bg-indigo-100 text-indigo-700 
            border border-indigo-200
          ">
            {plan.toUpperCase()}
          </span>

          {/* ---- PROFILE DROPDOWN ---- */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="focus:outline-none">
                <Avatar className="h-9 w-9 border border-white/40 shadow">
                  <AvatarFallback className="bg-indigo-100 text-indigo-700 font-semibold">
                    {user?.name?.[0] ?? "U"}
                  </AvatarFallback>
                </Avatar>
              </button>
            </DropdownMenuTrigger>

            <DropdownMenuContent
              align="end"
              className="w-56 backdrop-blur-xl bg-white/60 border-white/30 shadow-xl"
            >
              <DropdownMenuLabel className="text-neutral-900 text-sm">
                {user?.name}
              </DropdownMenuLabel>
              <p className="text-xs text-neutral-600 px-3 -mt-1 mb-1">
                {user?.email}
              </p>

              <DropdownMenuSeparator />

              <DropdownMenuItem className="flex items-center gap-2">
                <User2 className="h-4 w-4 opacity-70" />
                Profile
              </DropdownMenuItem>

              <DropdownMenuItem className="flex items-center gap-2">
                <Settings className="h-4 w-4 opacity-70" />
                Settings
              </DropdownMenuItem>

              <DropdownMenuSeparator />

              <DropdownMenuItem
                onClick={logout}
                className="flex items-center gap-2 text-red-600 focus:text-red-700"
              >
                <LogOut className="h-4 w-4 opacity-70" />
                Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </motion.header>
  );
}

