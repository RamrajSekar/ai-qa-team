"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/components/providers/AuthProvider";
import { 
  LayoutDashboard,
  Layers,
  Workflow,
  PlayCircle,
  Bot,
  Settings,
  LogOut
} from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const navItems = [
    { name: "Dashboard", href: "/dashboard", icon: <LayoutDashboard size={18} /> },
    { name: "Projects", href: "/projects", icon: <Layers size={18} /> },
    { name: "Scenarios", href: "/scenarios", icon: <Workflow size={18} /> },
    { name: "Executions", href: "/executions", icon: <PlayCircle size={18} /> },
    { name: "AI Generator", href: "/generator", icon: <Bot size={18} /> },
    { name: "Settings", href: "/settings", icon: <Settings size={18} /> },
  ];

  return (
    <aside className="w-64 h-screen bg-[#121214] border-r border-[#1F1F23] text-white flex flex-col">
      
      {/* Brand */}
      <div className="px-6 py-5 border-b border-[#1F1F23]">
        <h1 className="text-xl font-semibold tracking-tight">
          AI QA Team
        </h1>
        <p className="text-xs text-gray-400 mt-1">Logged in as</p>
        <p className="text-sm font-medium mt-1">{user?.name}</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const active = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`
                flex items-center gap-3 px-4 py-2 rounded-lg text-sm font-medium
                transition-all duration-150
                ${active
                  ? "bg-[#1F1F23] text-white border border-[#2A2A2D]"
                  : "text-gray-300 hover:bg-[#1A1A1D] hover:text-white"}
              `}
            >
              {item.icon}
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Plan Box */}
      <div className="px-4 py-4 border-t border-[#1F1F23]">
        <div className="bg-[#1A1A1D] rounded-xl p-4 text-center">
          <p className="text-xs text-gray-400">Your Plan</p>
          <p className="text-lg font-semibold mt-1">{user?.subscription?.plan?.toUpperCase()}</p>

          <Link
            href="/pricing"
            className="mt-3 block bg-[#3B82F6]/20 hover:bg-[#3B82F6]/30 text-blue-400 py-2 rounded-md text-sm font-medium transition"
          >
            Upgrade Plan
          </Link>
        </div>

        {/* Logout */}
        <button
          onClick={logout}
          className="mt-4 w-full flex items-center justify-center gap-2 text-gray-300 hover:text-white hover:bg-[#1A1A1D] py-2 rounded-lg transition"
        >
          <LogOut size={16} />
          Logout
        </button>
      </div>
    </aside>
  );
}
