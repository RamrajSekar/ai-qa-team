"use client";

import { useParams } from "next/navigation";
import TeamManager from "@/components/team/TeamManager";

export default function ProjectTeamPage() {
  const { projectId } = useParams<{ projectId: string }>();
  return <div><div className="workspace-page-header"><div><p className="workspace-eyebrow">Project settings</p><h1>Team</h1><p className="workspace-description">Manage project access and project-scoped roles.</p></div></div><TeamManager projectId={projectId} /></div>;
}
