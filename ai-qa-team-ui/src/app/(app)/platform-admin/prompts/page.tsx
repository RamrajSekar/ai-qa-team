"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import PlatformAdminGuard from "@/components/platform/PlatformAdminGuard";
import { useAuth } from "@/components/providers/AuthProvider";
import { apiFetch } from "@/utils/api";

interface PromptSummary { prompt_key: string; name: string; description: string; output_contract: string; resolved_version: number | string; source: string; }

export default function PromptsPage() {
  const { user } = useAuth();
  const canManagePrompts = user?.platform_role === "OWNER" || user?.platform_role === "ADMIN";
  const [prompts, setPrompts] = useState<PromptSummary[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!canManagePrompts) return;
    let current = true;
    apiFetch("/platform-admin/prompts").then(response => {
      if (!response.ok) throw new Error("Could not load platform prompts.");
      if (current) setPrompts(response.data);
    }).catch(() => { if (current) setError("Could not load platform prompts. Refresh the page to try again."); })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [canManagePrompts]);
  return <PlatformAdminGuard><div className="workspace-page-header"><div><p className="workspace-eyebrow">Platform administration</p><h1>Prompts</h1><p className="workspace-description">Manage platform instructions independently from provider and model configuration.</p></div></div><section className="workspace-panel"><div className="workspace-panel-body">{loading && <p role="status" className="workspace-empty">Loading platform prompts…</p>}{error && <p role="alert" className="workspace-empty">{error}</p>}{prompts.map((prompt) => <Link className="workspace-row" href={`/platform-admin/prompts/${prompt.prompt_key}`} key={prompt.prompt_key}><div><p className="workspace-row-title">{prompt.name}</p><p className="workspace-row-subtitle">{prompt.description}</p></div><div className="prompt-row-meta"><span className="workspace-badge">{prompt.output_contract}</span><span>{prompt.source === "CODE_FALLBACK" ? "Code Default" : `v${prompt.resolved_version}`}</span></div></Link>)}</div></section></PlatformAdminGuard>;
}
