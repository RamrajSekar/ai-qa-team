"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { useAuth } from "@/components/providers/AuthProvider";
import { useProjects } from "@/hooks/useProjects";
import { usePathname, useRouter } from "next/navigation";
import { ChevronDown, ChevronRight, LogOut, Sun, Moon, Monitor } from "lucide-react";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuRadioGroup, DropdownMenuRadioItem,
} from "@/components/ui/dropdown-menu";

export function Topbar() {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const router = useRouter();
  const pathname = usePathname();
  const { projects } = useProjects();
  const activeProjectId = pathname.match(/^\/projects\/([^/]+)/)?.[1];
  const project = projects.find((item) => item.project_id === activeProjectId);
  const pageName = pathname.split("/").filter(Boolean).pop() || "Workspace";

  return (
    <header className="workspace-topbar">
      <nav aria-label="Breadcrumb" className="workspace-breadcrumb">
        <Link href={activeProjectId ? "/projects" : "/dashboard"}>{activeProjectId ? "Projects" : "Workspace"}</Link>
        <ChevronRight size={14} aria-hidden="true" />
        <span>{project?.name || (activeProjectId ? activeProjectId : pageName.charAt(0).toUpperCase() + pageName.slice(1))}</span>
      </nav>
      <div className="workspace-account">
        <span className="workspace-badge">{user?.subscription?.plan || "free"} plan</span>
        {project && <DropdownMenu>
          <DropdownMenuTrigger asChild><button className="workspace-button workspace-project-switch" aria-label="Switch project">
            {project.name}<ChevronDown size={14} />
          </button></DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>Switch project</DropdownMenuLabel>
            {projects.map((item) => <DropdownMenuItem key={item.project_id} onSelect={() => router.push(`/projects/${item.project_id}`)}>{item.name}</DropdownMenuItem>)}
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => router.push("/projects")}>All projects</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>}
        <DropdownMenu>
          <DropdownMenuTrigger asChild><button className="workspace-avatar" aria-label="Account and appearance">{user?.name?.[0] || "U"}</button></DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-64">
            <DropdownMenuLabel>{user?.name || "Your account"}</DropdownMenuLabel>
            <p className="workspace-account-email">{user?.email}</p>
            <DropdownMenuSeparator />
            <DropdownMenuLabel>Appearance</DropdownMenuLabel>
            <DropdownMenuRadioGroup aria-label="Appearance" value={mounted ? theme : "system"} onValueChange={setTheme}>
              <DropdownMenuRadioItem value="light"><Sun size={16} />Light</DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="dark"><Moon size={16} />Dark</DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="system"><Monitor size={16} />System</DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" onSelect={logout}><LogOut size={16} />Sign out</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
