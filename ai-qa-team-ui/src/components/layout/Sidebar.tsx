"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/components/providers/AuthProvider";
import { usePathname } from "next/navigation";
import { useProjects } from "@/hooks/useProjects";


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
  Layers,
} from "lucide-react";

export default function Sidebar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const { projects } = useProjects();
  // Detect current project ID from URL
  const projectMatch = pathname.match(/^\/projects\/([^/]+)/);
  const currentProjectId = projectMatch ? projectMatch[1] : null;

  // pick 3 or 4 most recent projects
  const recent = projects.slice(0, 4);
  // Global Menu
  const globalMenu = [
    { name: "Dashboard", icon: <LayoutGrid size={18} />, href: "/dashboard" },
    { name: "Projects", icon: <FolderOpen size={18} />, href: "/projects" },
    { name: "AI Generator", icon: <Bot size={18} />, href: "/ai" },
    { name: "Settings", icon: <Settings size={18} />, href: "/settings" },
  ];

  // Project-specific menu (only when inside /projects/[id])
  const projectMenu = currentProjectId
    ? [
        {
          name: "Overview",
          icon: <Layers size={18} />,
          href: `/projects/${currentProjectId}`,
        },
        {
          name: "Environments",
          icon: <FolderOpen size={18} />,
          href: `/projects/${currentProjectId}/environments`,
        },
        {
          name: "Scenarios",
          icon: <Puzzle size={18} />,
          href: `/projects/${currentProjectId}/scenarios`,
        },
        {
          name: "Executions",
          icon: <Zap size={18} />,
          href: `/projects/${currentProjectId}/executions`,
        },
      ]
    : [];

  // Helper to highlight active menu
  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + "/");

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
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
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

      {/* GLOBAL MENU */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {globalMenu.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`group relative flex items-center gap-3 px-3 py-2 rounded-md transition cursor-pointer
              ${
                isActive(item.href)
                  ? "bg-purple-600 text-white shadow-md"
                  : "hover:bg-gray-800 text-gray-300"
              }
              ${collapsed ? "justify-center" : ""}
            `}
          >
            {isActive(item.href) && (
              <span className="absolute left-0 top-0 h-full w-1 bg-purple-400 rounded-r-md" />
            )}

            {item.icon}
            {!collapsed && <span>{item.name}</span>}
          </Link>
        ))}

        {/* PROJECT MENU */}
        {currentProjectId && (
          <>
            {!collapsed && (
              <p className="mt-4 mb-2 text-xs uppercase text-gray-500">
                Project
              </p>
            )}

            {projectMenu.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`group relative flex items-center gap-3 px-3 py-2 rounded-md transition cursor-pointer
                ${
                  isActive(item.href)
                    ? "bg-purple-600 text-white shadow-md"
                    : "hover:bg-gray-800 text-gray-300"
                }
                ${collapsed ? "justify-center" : ""}
              `}
              >
                {isActive(item.href) && (
                  <span className="absolute left-0 top-0 h-full w-1 bg-purple-400 rounded-r-md" />
                )}

                {item.icon}
                {!collapsed && <span>{item.name}</span>}
              </Link>
            ))}
          </>
        )}
      </nav>
      {/* RECENT PROJECTS */}
      {!collapsed && recent.length > 0 && (
        <div className="px-4 py-4 border-t border-gray-700">
          <p className="text-xs uppercase text-gray-500 mb-2">Recent Projects</p>
          {recent.map((p) => (
            <Link
              key={p.project_id}
              href={`/projects/${p.project_id}`}
              className={`block text-sm py-1.5 rounded hover:bg-gray-800 px-2 ${
                pathname.includes(p.project_id) ? "bg-purple-600 text-white" : "text-gray-300"
              }`}
            >
              {p.name}
            </Link>
          ))}
        </div>
      )}

      {/* Collapsed mode */}
      {collapsed && recent.length > 0 && (
        <div className="px-2 py-4 border-t border-gray-700 flex flex-col gap-3">
          {recent.map((p) => (
            <Link
              key={p.project_id}
              href={`/projects/${p.project_id}`}
              className={`w-10 h-10 rounded-md flex items-center justify-center text-xs hover:bg-gray-800 ${
                pathname.includes(p.project_id) ? "bg-purple-600" : "bg-gray-800"
              }`}
            >
              {p.name[0]}
            </Link>
          ))}
        </div>
      )}

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
