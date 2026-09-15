"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useProjects } from "@/hooks/useProjects";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";
import { LayoutGrid, FolderOpen, Puzzle, Zap, Bot, ChevronLeft, ChevronRight, Layers, FileText } from "lucide-react";

export default function Sidebar() {
  const { enabled } = useFeatures();
  const pathname = usePathname();
  const { projects } = useProjects();
  const [collapsed, setCollapsed] = useState(false);
  const projectId = pathname.match(/^\/projects\/([^/]+)/)?.[1];
  const project = projects.find((item) => item.project_id === projectId);
  const globalMenu = [
    { name: "Dashboard", icon: LayoutGrid, href: "/dashboard" },
    { name: "Projects", icon: FolderOpen, href: "/projects" },
    ...(enabled("test_generation") ? [{ name: "AI Generator", icon: Bot, href: "/ai" }] : []),
  ];
  const projectMenu = projectId ? [
    { name: "Overview", icon: Layers, href: `/projects/${projectId}` },
    ...(enabled("story_management") ? [{ name: "Stories", icon: FileText, href: `/projects/${projectId}/stories` }] : []),
    { name: "Environments", icon: FolderOpen, href: `/projects/${projectId}/environments` },
    ...(enabled("scenario_generation") ? [{ name: "Scenarios", icon: Puzzle, href: `/projects/${projectId}/scenarios` }] : []),
    // Execution history is shown on the overview; there is no separate execution page yet.
  ] : [];
  const destination = [...globalMenu, ...projectMenu].filter((item) => pathname === item.href || pathname.startsWith(item.href + "/"))
    .sort((a, b) => b.href.length - a.href.length)[0]?.href;

  return (
    <aside className={`workspace-sidebar ${collapsed ? "is-collapsed" : ""}`} aria-label="Workspace navigation">
      <div className="workspace-brand"><Link href="/dashboard" aria-label="AI QA Team dashboard"><span className="workspace-logo">QA</span><strong>AI QA Team</strong></Link>
        <button onClick={() => setCollapsed(!collapsed)} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} aria-expanded={!collapsed}>
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>
      <nav className="workspace-nav">
        <p className="workspace-nav-label">Workspace</p>
        {globalMenu.map(({ name, icon: Icon, href }) => <Link key={href} href={href} title={name} aria-label={name} aria-current={destination === href ? "page" : undefined} className="workspace-nav-link"><Icon size={18} /><span>{name}</span></Link>)}
        {projectId && <>
          <p className="workspace-nav-label workspace-project-label" title={project?.name}>{project?.name || "Current project"}</p>
          {projectMenu.map(({ name, icon: Icon, href }) => <Link key={href} href={href} title={name} aria-label={name} aria-current={destination === href ? "page" : undefined} className="workspace-nav-link"><Icon size={18} /><span>{name}</span></Link>)}
          <Link href={`/projects/${projectId}#execution-history`} title="Execution history" aria-label="Execution history" className="workspace-nav-link"><Zap size={18} /><span>Execution history</span></Link>
        </>}
        {projects.length > 0 && <div className="workspace-recent"><p className="workspace-nav-label">Recent projects</p>
          {projects.slice(0, 4).map((item) => <Link key={item.project_id} href={`/projects/${item.project_id}`} title={item.name} className="workspace-recent-link"><span className="workspace-project-dot" /><span>{item.name}</span></Link>)}
        </div>}
      </nav>
      <div className="workspace-sidebar-footer"><span className="workspace-status-dot" /><span>Your QA workspace</span></div>
    </aside>
  );
}
