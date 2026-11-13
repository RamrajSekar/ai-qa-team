"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useProjects } from "@/hooks/useProjects";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";
import { useAuth } from "@/components/providers/AuthProvider";
import { LayoutGrid, FolderOpen, Zap, ChevronLeft, ChevronRight, Layers, FileText, GitBranch, Users, BrainCircuit, ShieldCheck, MessageSquareText, Bug } from "lucide-react";

export default function Sidebar() {
  const { enabled } = useFeatures();
  const { user } = useAuth();
  const pathname = usePathname();
  const { projects } = useProjects();
  const [collapsed, setCollapsed] = useState(false);
  const projectId = pathname.match(/^\/projects\/([^/]+)/)?.[1];
  const project = projects.find((item) => item.project_id === projectId);
  const globalMenu = [
    { name: "Dashboard", icon: LayoutGrid, href: "/dashboard" },
    ...(enabled("customer_accounts") ? [{ name: "Account", icon: Users, href: "/settings/account" }] : []),
    ...(projects.some(item => item.current_user_role === "ADMIN") ? [{ name: "AI Configuration", icon: BrainCircuit, href: "/settings/ai" }] : []),
    { name: "Projects", icon: FolderOpen, href: "/projects" },
  ];
  const platformMenu = user?.platform_role === "OWNER" || user?.platform_role === "ADMIN" ? [
    { name: "Admin Dashboard", icon: ShieldCheck, href: "/platform-admin" },
    { name: "Prompts", icon: MessageSquareText, href: "/platform-admin/prompts" },
  ] : [];
  const projectMenu = projectId ? [
    { name: "Overview", icon: Layers, href: `/projects/${projectId}` },
    ...(enabled("product_knowledge") ? [{ name: "Product Knowledge", icon: BrainCircuit, href: `/projects/${projectId}/knowledge` }] : []),
    ...(enabled("visual_runner_lab") ? [{ name: "Visual Runner Lab", icon: Zap, href: `/projects/${projectId}/visual-lab` }] : []),
    ...(enabled("bug_reproduction_ui") ? [{ name: "Reproduce Bug", icon: Bug, href: `/projects/${projectId}/reproduce` }] : []),
    ...(enabled("story_management") ? [{ name: "Stories", icon: FileText, href: `/projects/${projectId}/stories` }] : []),
    ...(enabled("scenario_generation") ? [{ name: "Scenarios", icon: Layers, href: `/projects/${projectId}/scenarios` }] : []),
    ...(enabled("test_generation") ? [{ name: "Test Cases", icon: FileText, href: `/projects/${projectId}/testcases` }] : []),
    ...(enabled("test_execution_ui", "test_generation", "approved_visual_run_admission") ? [{ name: "Test Execution", icon: Zap, href: `/projects/${projectId}/test-execution` }] : []),
    { name: "Environments", icon: FolderOpen, href: `/projects/${projectId}/environments` },
    ...(enabled("repository_ui", "repository_discovery", "test_registry") ? [{ name: "Repositories", icon: GitBranch, href: `/projects/${projectId}/repositories` }] : []),
    ...(!enabled("customer_accounts") && project?.current_user_role === "ADMIN" ? [{ name: "Team", icon: Users, href: `/projects/${projectId}/settings/team` }] : []),
    { name: "Execution history", icon: Zap, href: `/projects/${projectId}/execution-history` },
  ] : [];
  const destination = [...globalMenu, ...platformMenu, ...projectMenu].filter((item) => pathname === item.href || pathname.startsWith(item.href + "/"))
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
        {platformMenu.length > 0 && <><p className="workspace-nav-label">Platform Admin</p>{platformMenu.map(({ name, icon: Icon, href }) => <Link key={href} href={href} title={name} aria-label={name} aria-current={destination === href ? "page" : undefined} className="workspace-nav-link"><Icon size={18} /><span>{name}</span></Link>)}</>}
        {projectId && <>
          <p className="workspace-nav-label workspace-project-label" title={project?.name}>{project?.name || "Current project"}</p>
          {projectMenu.map(({ name, icon: Icon, href }) => <Link key={href} href={href} title={name} aria-label={name} aria-current={destination === href ? "page" : undefined} className="workspace-nav-link"><Icon size={18} /><span>{name}</span></Link>)}
        </>}
        {projects.length > 0 && <div className="workspace-recent"><p className="workspace-nav-label">Recent projects</p>
          {projects.slice(0, 4).map((item) => <Link key={item.project_id} href={`/projects/${item.project_id}`} title={item.name} className="workspace-recent-link"><span className="workspace-project-dot" /><span>{item.name}</span></Link>)}
        </div>}
      </nav>
      <div className="workspace-sidebar-footer"><span className="workspace-status-dot" /><span>Your QA workspace</span></div>
    </aside>
  );
}
