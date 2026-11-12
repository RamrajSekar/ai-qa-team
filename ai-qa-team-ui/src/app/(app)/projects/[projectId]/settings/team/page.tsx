"use client";

import Link from "next/link";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";
import { useParams } from "next/navigation";
import TeamManager from "@/components/team/TeamManager";

export default function ProjectTeamPage() {
  const { enabled } = useFeatures();
  const { projectId } = useParams<{ projectId: string }>();
  if (enabled("customer_accounts")) return <div className="design-page"><h1>Team management moved</h1><Link className="workspace-button" href="/settings/account/team">Open Account → Team</Link></div>;
  return <div><div className="workspace-page-header"><div><p className="workspace-eyebrow">Project settings</p><h1>Team</h1><p className="workspace-description">Manage project access and project-scoped roles.</p></div></div><TeamManager projectId={projectId} /></div>;
}
