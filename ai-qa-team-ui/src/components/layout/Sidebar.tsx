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
  Info,
} from "lucide-react";

export default function Sidebar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  const { projects } = useProjects();

  // detect active project
  const match = pathname.match(/^\/projects\/([^/]+)/);
  const currentProjectId = match ? match[1] : null;

  // global menu
  const globalMenu = [
    { name: "Dashboard", icon: <LayoutGrid size={18} />, href: "/dashboard" },
    { name: "Projects", icon: <FolderOpen size={18} />, href: "/projects" },
    { name: "AI Generator", icon: <Bot size={18} />, href: "/ai" },
    { name: "Settings", icon: <Settings size={18} />, href: "/settings" },
  ];

  // project menu
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

  // highlighting logic
  const isActiveGlobal = (href: string) => pathname === href;
  const isActiveProject = (href: string) =>
    pathname === href || pathname.startsWith(href + "/");

  // recent projects
  const recent = projects.slice(0, 4);

  return (
    <aside
      className={`h-screen flex flex-col bg-gray-900 text-white transition-all duration-300 ${
        collapsed ? "w-16" : "w-64"
      } shadow-xl`}
    >
      {/* HEADER */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-lg bg-purple-600 flex items-center justify-center font-bold shadow">
            QA
          </div>

          {!collapsed && (
            <span className="font-semibold text-lg whitespace-nowrap tracking-tight">
              AI QA Team
            </span>
          )}
        </div>

        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1 rounded-md hover:bg-gray-800 transition"
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      {/* USER SECTION */}
      <div className="px-4 py-3 text-gray-300 text-sm border-b border-gray-700">
        {!collapsed ? (
          <>
            <p className="text-xs opacity-60">Logged in as</p>
            <p className="font-medium truncate">{user?.name || "User"}</p>
          </>
        ) : (
          <div className="mx-auto text-center w-full text-xs opacity-70 font-medium">
            {user?.name?.[0] || "U"}
          </div>
        )}
      </div>

      {/* NAVIGATION */}
      <nav className="flex-1 px-2 py-4 space-y-1 relative">
        {/* GLOBAL SECTION */}
        {!collapsed && (
          <p className="text-xs uppercase text-gray-500 px-3 flex items-center gap-2 mb-1 tracking-wide">
            <Info size={12} /> Global
          </p>
        )}

        {globalMenu.map((item) => {
          const active = isActiveGlobal(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`
                group relative flex items-center gap-3 px-3 py-2 rounded-md 
                transition-all cursor-pointer font-medium
                ${
                  active
                    ? "bg-purple-600 shadow-lg text-white"
                    : "hover:bg-gray-800 text-gray-300"
                }
                ${collapsed ? "justify-center" : ""}
              `}
            >
              {active && (
                <span className="absolute left-0 top-0 h-full w-1 bg-purple-400 rounded-r-md"></span>
              )}

              {item.icon}
              {!collapsed && <span>{item.name}</span>}

              {/* Tooltip for collapsed mode */}
              {collapsed && (
                <span
                  className="absolute left-14 opacity-0 group-hover:opacity-100 text-xs px-2 py-1 bg-black/80 rounded 
                  pointer-events-none transition whitespace-nowrap"
                >
                  {item.name}
                </span>
              )}
            </Link>
          );
        })}

        {/* PROJECT SECTION */}
        {currentProjectId && (
          <>
            {!collapsed && (
              <p className="text-xs uppercase text-gray-500 px-3 mt-5 mb-1 tracking-wide flex items-center gap-2">
                <FolderOpen size={12} /> Project
              </p>
            )}

            {projectMenu.map((item) => {
              const active = isActiveProject(item.href);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`
                  group relative flex items-center gap-3 px-3 py-2 rounded-md 
                  transition cursor-pointer font-medium
                  ${
                    active
                      ? "bg-purple-600 text-white shadow-lg"
                      : "hover:bg-gray-800 text-gray-300"
                  }
                  ${collapsed ? "justify-center" : ""}
                `}
                >
                  {active && (
                    <span className="absolute left-0 top-0 h-full w-1 bg-purple-400"></span>
                  )}

                  {item.icon}
                  {!collapsed && <span>{item.name}</span>}

                  {/* Tooltip collapsed */}
                  {collapsed && (
                    <span className="absolute left-14 opacity-0 group-hover:opacity-100 text-xs px-2 py-1 bg-black/70 rounded-md">
                      {item.name}
                    </span>
                  )}
                </Link>
              );
            })}
          </>
        )}

        {/* RECENT PROJECTS */}
        {!collapsed && recent.length > 0 && (
          <div className="mt-6 pt-4 border-t border-gray-700">
            <p className="text-xs uppercase text-gray-500 px-3 mb-2 tracking-wide">
              Recent Projects
            </p>

            {recent.map((p) => (
              <Link
                key={p.project_id}
                href={`/projects/${p.project_id}`}
                className={`block text-sm py-1.5 rounded px-3 mb-1 transition
                ${
                  pathname.includes(p.project_id)
                    ? "bg-purple-700 text-white shadow-md"
                    : "hover:bg-gray-800 text-gray-300"
                }`}
              >
                {p.name}
              </Link>
            ))}
          </div>
        )}

        {/* Collapsed Recent */}
        {collapsed && recent.length > 0 && (
          <div className="px-2 mt-4 border-t border-gray-700 flex flex-col items-center gap-3 pt-4">
            {recent.map((p) => (
              <Link
                key={p.project_id}
                href={`/projects/${p.project_id}`}
                className={`
                  w-10 h-10 flex items-center justify-center rounded-md text-xs 
                  ${
                    pathname.includes(p.project_id)
                      ? "bg-purple-600"
                      : "bg-gray-800 hover:bg-gray-700"
                  }
                `}
              >
                {p.name[0]}
              </Link>
            ))}
          </div>
        )}
      </nav>

      {/* PLAN BOX */}
      <div className="p-4 border-t border-gray-800 text-center">
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

      {/* LOGOUT */}
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
