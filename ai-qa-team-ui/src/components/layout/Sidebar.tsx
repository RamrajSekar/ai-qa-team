"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  FolderOpen,
  Binary,
  PlayCircle,
  Settings,
  Zap,
} from "lucide-react";
import { useAuth } from "@/components/providers/AuthProvider";
import { toast } from "sonner";

const API_URL = process.env.NEXT_PUBLIC_API_URL as string;

const nav = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Projects", href: "/projects", icon: FolderOpen },
  { label: "Scenarios", href: "/scenarios", icon: Binary },
  { label: "Executions", href: "/executions", icon: PlayCircle },
  { label: "AI Generator", href: "/ai", icon: Zap },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const { user, setUser } = useAuth();
  const pathname = usePathname();

  async function upgradePlan() {
    try {
      const res = await fetch(`${API_URL}/auth/upgrade-plan?plan=pro`, {
        method: "PATCH",
        credentials: "include",
      });

      const json = await res.json();

      // Optimistically update UI (no prev → assign full user)
      setUser({
        ...user!,
        subscription: json.subscription,
      });

      toast.success("Upgraded to PRO!");
    } catch (err) {
      toast.error("Upgrade failed");
    }
  }

  return (
    <motion.aside
      initial={{ x: -18, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.35 }}
      className="
        w-64 shrink-0 p-5 
        backdrop-blur-2xl 
        bg-[#1a1a1f]/60 
        border-r border-white/10
        text-gray-200 flex flex-col
      "
    >
      {/* Logo */}
      <div className="mb-10 flex items-center gap-3">
        <div className="h-9 w-9 rounded-xl bg-gray-700/60 flex items-center justify-center font-bold text-white shadow">
          QA
        </div>
        <h1 className="font-semibold text-lg tracking-wide text-gray-100">
          AI QA Team
        </h1>
      </div>

      {/* Navigation */}
      <nav className="flex flex-col gap-1">
        {nav.map((item) => {
          const active = pathname.startsWith(item.href);

          return (
            <Link key={item.href} href={item.href}>
              <motion.div
                whileHover={{ scale: 1.02 }}
                className={`
                  flex items-center gap-3 px-3 py-3 rounded-xl cursor-pointer
                  transition-all
                  ${
                    active
                      ? "bg-gray-700/70 text-white shadow-lg"
                      : "text-gray-300 hover:bg-gray-700/30"
                  }
                `}
              >
                <item.icon size={18} />
                <span>{item.label}</span>
              </motion.div>
            </Link>
          );
        })}
      </nav>

      {/* Plan Box */}
      <div
        className="
          mt-auto p-4 rounded-2xl 
          backdrop-blur-xl bg-white/5 
          border border-white/10
        "
      >
        <p className="text-xs text-gray-400">Your Plan</p>
        <p className="text-lg font-semibold mt-1 text-gray-100">
          {user?.subscription?.plan?.toUpperCase() ?? "FREE"}
        </p>

        {user?.subscription?.plan !== "pro" && (
          <button
            onClick={upgradePlan}
            className="
              mt-3 w-full rounded-xl 
              bg-gray-700/60 text-white 
              px-4 py-2 text-sm
              font-medium 
              hover:bg-gray-700/80 
              transition shadow
            "
          >
            Upgrade Plan
          </button>
        )}
      </div>
    </motion.aside>
  );
}
