"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import RepositoryManager from "@/components/repositories/RepositoryManager";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";
import { apiFetch } from "@/utils/api";

export default function RepositoriesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { enabled, ready } = useFeatures();
  const [role, setRole] = useState<"ADMIN" | "TESTER" | null>(null);
  useEffect(() => { apiFetch(`/projects/${projectId}`).then((response) => setRole(response.ok && response.data.current_user_role === "ADMIN" ? "ADMIN" : "TESTER")); }, [projectId]);
  if (!ready) return <p role="status">Loading repositories…</p>;
  if (!enabled("repository_discovery", "test_registry")) return <p>This feature is disabled.</p>;
  if (role === null) return <p role="status">Loading project access…</p>;

  return <div><div className="workspace-page-header"><div><p className="workspace-eyebrow">Automation</p><h1>Repositories</h1><p className="workspace-description">Connect your existing automation repository. AI QA Team will discover automated tests without requiring you to rewrite them.</p></div></div><RepositoryManager projectId={projectId} readOnly={role === "TESTER"} /></div>;
}
