"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/components/providers/AuthProvider";
import { usePathname } from "next/navigation";

import {
  LayoutGrid,
  FolderOpen,
  Puzzle,
  Zap,
  Bot,
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
} from "lucide-react";

export default function Sidebar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  const menu = [
    { name: "Dashboard", icon: <LayoutGrid size={18} />, href: "/dashboard" },
    { name: "Projects", icon: <FolderOpen size={18} />, href: "/projects" },
    { name: "Scenarios", icon: <Puzzle size={18} />, href: "/scenarios" },
    { name: "Executions", icon: <Zap size={18} />, href: "/executions" },
    { name: "AI Generator", icon: <Bot size={18} />, href: "/ai" },
    { name: "Settings", icon: <Settings size={18} />, href: "/settings" },
  ];

  return (
    <aside
      className={`h-screen flex flex-col bg-gray-900 text-white transition-all duration-300 ${
        collapsed ? "w-16" : "w-64"
      }`}
    >
      {/* HEADER */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-purple-500 flex items-center justify-center font-bold">
            QA
          </div>

          {!collapsed && (
            <span className="font-semibold text-lg whitespace-nowrap">
              AI QA Team
            </span>
          )}
        </div>

        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1 rounded-md hover:bg-gray-800"
        >
          {collapsed ? (
            <ChevronRight size={18} />
          ) : (
            <ChevronLeft size={18} />
          )}
        </button>
      </div>

      {/* USER */}
      <div className="px-4 py-3 text-gray-300 text-sm border-b border-gray-700">
        {!collapsed ? (
          <>
            <p className="text-xs opacity-60">Logged in as</p>
            <p className="font-medium">{user?.name || "User"}</p>
          </>
        ) : (
          <div className="mx-auto text-center w-full text-xs opacity-70">
            {user?.name?.[0] || "U"}
          </div>
        )}
      </div>

      {/* MENU */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {menu.map((item) => {
          const active = pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`
                group relative flex items-center gap-3 px-3 py-2 rounded-md 
                transition cursor-pointer
                ${
                  active
                    ? "bg-purple-600 text-white shadow-md"
                    : "hover:bg-gray-800 text-gray-300"
                }
                ${collapsed ? "justify-center" : ""}
              `}
            >
              {/* PURPLE ACCENT BAR (left side) */}
              {active && (
                <span
                  className="absolute left-0 top-0 h-full w-1 bg-purple-400 rounded-r-md"
                />
              )}

              {item.icon}
              {!collapsed && <span>{item.name}</span>}
            </Link>
          );
        })}
      </nav>

      {/* PLAN BOX */}
      <div className="p-4 border-t border-gray-700 text-center">
        {!collapsed ? (
          <>
            <p className="text-xs">Your Plan</p>
            <p className="text-lg font-semibold">
              {user?.subscription?.plan || "FREE"}
            </p>

            <Link
              href="/pricing"
              className="mt-2 inline-block bg-purple-500 text-white px-4 py-2 text-xs rounded-md hover:bg-purple-600"
            >
              Upgrade Plan
            </Link>
          </>
        ) : (
          <p className="text-xs font-semibold">
            {(user?.subscription?.plan || "F")[0]}
          </p>
        )}
      </div>

      {/* LOGOUT BUTTON */}
      <div className="border-t border-gray-800 p-4">
        <button
          onClick={logout}
          className={`flex items-center gap-3 w-full text-left
            px-3 py-2 rounded-md text-red-400 hover:bg-red-900/30 transition
            ${collapsed ? "justify-center" : ""}
          `}
        >
          <LogOut size={18} />
          {!collapsed && <span>Logout</span>}
        </button>
      </div>
    </aside>
  );
}
