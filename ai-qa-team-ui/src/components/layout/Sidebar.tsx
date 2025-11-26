"use client";

import Link from "next/link";
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
import { usePathname } from "next/navigation";

const nav = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Projects", href: "/projects", icon: FolderOpen },
  { label: "Scenarios", href: "/scenarios", icon: Binary },
  { label: "Executions", href: "/executions", icon: PlayCircle },
  { label: "AI Generator", href: "/ai", icon: Zap },
  { label: "Settings", href: "/settings", icon: Settings },
];

export default function Sidebar() {
  const { user } = useAuth();
  console.log("SIDEBAR USER:", user);
  const pathname = usePathname();
  const activeColor = "bg-[#6A5ACD]/90 text-white shadow-lg"; // SlateBlue
  const hoverColor = "hover:bg-white/10";

  return (
    <motion.aside
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="
        w-64 shrink-0 p-5 
        backdrop-blur-2xl 
        bg-[#1a1b1f]/60
        border-r border-white/10
        text-white flex flex-col
      "
    >
      {/* Logo */}
      <div className="flex items-center gap-2 mb-6">
        <div className="h-9 w-9 rounded-xl bg-[#6A5ACD] flex items-center justify-center font-bold">
          QA
        </div>
        <h1 className="font-semibold text-lg tracking-wide">AI QA Team</h1>
      </div>

      {/* 👤 User Name */}
      <div className="mb-8 text-sm text-gray-300 pl-1">
        <span className="text-gray-400">Logged in as</span>
        <div className="text-white font-medium text-base mt-1">
          {user?.name ?? "User"}
        </div>
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
                  ${active ? activeColor : `text-gray-300 ${hoverColor}`}
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

        <p className="text-lg font-semibold mt-1">
          {user?.subscription?.plan?.toUpperCase() ?? "FREE"}
        </p>

        <Link
          href="/pricing"
          className="mt-3 block rounded-lg bg-[#6A5ACD] text-white text-center text-sm py-2 hover:bg-[#7a6bf0]"
        >
          Upgrade Plan
        </Link>
      </div>
    </motion.aside>
  );
}
